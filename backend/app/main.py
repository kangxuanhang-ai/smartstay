from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import init_db
from app.core.seed import seed_default_staff, seed_default_rooms, seed_hotel_info, seed_facilities
from app.api import auth, rooms, orders, work_orders, admin, consumptions
from app.api import hotel
from app.api.ai import router as ai_router
from app.api.face import router as face_router
from app.api.rag import router as rag_router
from app.api.alipay import router as alipay_router
from app.ws.manager import manager

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # 生产环境不自动 seed（通过独立脚本手动执行）
    if settings.ENVIRONMENT != "production":
        await seed_default_staff()
        await seed_default_rooms()
        await seed_hotel_info()
        await seed_facilities()

    # Create Aliyun face database on startup (safe to call repeatedly)
    try:
        from app.aliyun.face import create_face_db
        import asyncio
        await asyncio.to_thread(create_face_db, settings.ALIYUN_FACE_DB_NAME)
    except Exception:
        pass  # DB may already exist

    from app.tasks.audit import generate_audit_report
    scheduler.add_job(generate_audit_report, 'cron', hour=4, minute=0, id='daily_audit', replace_existing=True)
    from app.core.utils import cst_now
    scheduler.add_job(generate_audit_report, 'date', run_date=cst_now() + timedelta(seconds=30), id='initial_audit')
    scheduler.start()

    yield

    scheduler.shutdown()


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="SmartStay API", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    detail = str(exc) if settings.ENVIRONMENT != "production" else "请联系管理员"
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "detail": detail},
    )

_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(orders.router)
app.include_router(work_orders.router)
app.include_router(admin.router)
app.include_router(consumptions.router)
app.include_router(hotel.router)
app.include_router(ai_router)
app.include_router(rag_router)
app.include_router(face_router)
app.include_router(alipay_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    import asyncio
    token = websocket.query_params.get("token", "")
    try:
        result = await manager.connect(websocket, token)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("WebSocket connect error: %s", e, exc_info=True)
        return
    if not result:
        return
    user_id, role = result

    async def send_pings():
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    ping_task = asyncio.create_task(send_pings())
    try:
        while True:
            data = await websocket.receive_text()
            # Respond to pong from client (optional, just keep connection alive)
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        manager.disconnect(user_id, websocket)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
