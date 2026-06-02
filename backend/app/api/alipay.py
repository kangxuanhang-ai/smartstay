import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sa_update

from app.core.database import get_db
from app.core.deps import require_role
from app.core.config import settings
from app.core.utils import cst_now
from app.models.user import Staff
from app.models.order import Order
from app.models.room import Room
from app.ws.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["alipay"])


def _format_pem_key(key: str, key_type: str = "RSA PRIVATE") -> str:
    """Wrap a raw base64 key in PEM format if it doesn't already have headers."""
    if key.startswith("-----BEGIN"):
        return key
    return f"-----BEGIN {key_type} KEY-----\n{key}\n-----END {key_type} KEY-----"


def _get_alipay_client():
    """Create a configured Alipay client using sandbox mode."""
    from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
    from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient

    config = AlipayClientConfig()
    config.sandbox_debug = True
    config.app_id = settings.ALIPAY_APP_ID
    config.app_private_key = _format_pem_key(settings.ALIPAY_PRIVATE_KEY, "RSA PRIVATE")
    config.alipay_public_key = _format_pem_key(settings.ALIPAY_PUBLIC_KEY, "PUBLIC")
    config.sign_type = "RSA2"
    config.timeout = 15

    return DefaultAlipayClient(alipay_client_config=config, logger=logger)


def _verify_alipay_signature(params: dict, signature: str) -> bool:
    """Verify Alipay RSA2 signature on async notification."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, utils
    import base64

    # Build the unsigned content string: all params except sign and sign_type, sorted by key
    unsigned_items = [
        (k, v)
        for k, v in sorted(params.items())
        if k not in ("sign", "sign_type") and v
    ]
    unsigned_string = "&".join(f"{k}={v}" for k, v in unsigned_items)

    try:
        # Load Alipay public key
        pub_key_pem = settings.ALIPAY_PUBLIC_KEY
        if not pub_key_pem.startswith("-----BEGIN"):
            pub_key_pem = (
                f"-----BEGIN PUBLIC KEY-----\n"
                f"{pub_key_pem}\n"
                f"-----END PUBLIC KEY-----"
            )
        public_key = serialization.load_pem_public_key(pub_key_pem.encode())

        # Verify RSA2 (SHA256WithRSA)
        signature_bytes = base64.b64decode(signature)
        public_key.verify(
            signature_bytes,
            unsigned_string.encode(),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as e:
        logger.warning("Alipay signature verification failed: %s", e)
        return False


@router.post("/orders/{order_id}/create-alipay-order")
async def create_alipay_order(
    order_id: str,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    """Create an Alipay sandbox payment order for checkout."""
    from app.api.orders import get_bill_total

    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "checked_in":
        raise HTTPException(status_code=409, detail="订单状态不正确，只有已入住订单可以支付")

    total = await get_bill_total(db, order.id)
    if total <= 0:
        raise HTTPException(status_code=400, detail="账单金额为零，无需支付")

    from alipay.aop.api.domain.AlipayTradePagePayModel import AlipayTradePagePayModel
    from alipay.aop.api.request.AlipayTradePagePayRequest import AlipayTradePagePayRequest

    alipay_client = _get_alipay_client()

    model = AlipayTradePagePayModel()
    model.out_trade_no = str(order.id)
    model.total_amount = round(total / 100, 2)
    model.subject = f"SmartStay 退房支付 - 订单 {str(order.id)[:8]}"
    model.product_code = "FAST_INSTANT_TRADE_PAY"

    alipay_request = AlipayTradePagePayRequest(biz_model=model)
    alipay_request.notify_url = settings.ALIPAY_NOTIFY_URL

    pay_url = alipay_client.page_execute(alipay_request, http_method="GET")
    return {"pay_url": pay_url, "amount": model.total_amount, "order_id": str(order.id)}


@router.post("/alipay/notify")
async def alipay_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Async callback from Alipay after payment completion."""
    form = await request.form()
    params = {k: v for k, v in form.items()}

    sign = params.get("sign", "")
    if not sign:
        logger.warning("Alipay notify: missing signature")
        raise HTTPException(status_code=400, detail="缺少签名")

    if not _verify_alipay_signature(params, sign):
        logger.warning("Alipay notify: signature verification failed")
        raise HTTPException(status_code=400, detail="签名验证失败")

    trade_status = params.get("trade_status")
    out_trade_no = params.get("out_trade_no")
    total_amount = params.get("total_amount")

    logger.info(
        "Alipay notify: out_trade_no=%s, trade_status=%s, total_amount=%s",
        out_trade_no,
        trade_status,
        total_amount,
    )

    if trade_status == "TRADE_SUCCESS":
        result = await db.execute(select(Order).where(Order.id == uuid.UUID(out_trade_no)))
        order = result.scalar_one_or_none()
        if order and order.status == "checked_in":
            order.status = "checked_out"
            order.check_out_time = cst_now()
            await db.execute(
                sa_update(Room).where(Room.id == order.room_id).values(status="dirty")
            )
            await db.commit()

            await manager.broadcast_biz({
                "event": "room.status_change",
                "data": {"room_id": str(order.room_id), "old_status": "occupied", "new_status": "dirty"},
            })
            logger.info("Alipay notify: order %s checked out successfully", out_trade_no)
        else:
            logger.warning(
                "Alipay notify: order %s not found or not in checked_in status", out_trade_no
            )

    # Return "success" to Alipay to acknowledge receipt
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("success")
