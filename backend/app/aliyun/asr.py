"""阿里云语音识别（一句话识别 REST API）封装"""

import base64
import hashlib
import hmac
import time
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

import httpx

from app.core.config import settings

# 阿里云一句话识别 REST API
_ASR_URL = "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/asr"
_TOKEN_URL = "https://nls-meta.cn-shanghai.aliyuncs.com/"

_FORMAT_MAP = {
    "m4a": "aac",
    "aac": "aac",
    "wav": "pcm",
    "mp3": "mp3",
    "ogg": "ogg",
    "amr": "amr",
    "webm": "opus",
}


async def _get_token() -> str:
    """获取阿里云 NLS Access Token"""
    params = {
        "Action": "CreateToken",
        "AccessKeyId": settings.ALIYUN_ACCESS_KEY_ID,
        "Format": "JSON",
        "RegionId": settings.ALIYUN_REGION_ID,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(int(time.time() * 1000)),
        "SignatureVersion": "1.0",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2019-02-28",
    }

    sorted_params = sorted(params.items())
    query_string = urlencode(sorted_params, quote_via=quote)
    string_to_sign = f"GET&%2F&{quote(query_string, safe='')}"
    sign_key = settings.ALIYUN_ACCESS_KEY_SECRET + "&"
    signature = base64.b64encode(
        hmac.new(sign_key.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    params["Signature"] = signature

    async with httpx.AsyncClient(proxy=None) as client:
        resp = await client.get(_TOKEN_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data["Token"]["Id"]


async def transcribe_audio(audio_bytes: bytes, audio_format: str = "m4a") -> str:
    """
    调用阿里云一句话识别 REST API，返回识别文字。

    Args:
        audio_bytes: 音频文件字节数据
        audio_format: 音频格式 (m4a/wav/mp3/webm)

    Returns:
        识别出的文字

    Raises:
        ValueError: 音频为空或识别结果为空
        RuntimeError: ASR 服务调用失败
    """
    if not audio_bytes:
        raise ValueError("音频数据为空")

    if not settings.ALIYUN_ASR_APP_KEY:
        raise RuntimeError("ALIYUN_ASR_APP_KEY 未配置")

    token = await _get_token()

    nls_format = _FORMAT_MAP.get(audio_format, "aac")

    # 一句话识别 REST API：query params + raw audio bytes in body
    params = {
        "appkey": settings.ALIYUN_ASR_APP_KEY,
        "format": nls_format,
        "sample_rate": 16000,
        "enable_punctuation_prediction": True,
        "enable_inverse_text_normalization": True,
    }

    headers = {
        "Content-Type": "application/octet-stream",
        "X-NLS-Token": token,
    }

    async with httpx.AsyncClient(timeout=30.0, proxy=None) as client:
        resp = await client.post(
            _ASR_URL,
            params=params,
            content=audio_bytes,
            headers=headers,
        )
        resp.raise_for_status()
        result = resp.json()

    if result.get("status") != 20000000:
        raise RuntimeError(f"ASR 识别失败: {result.get('message', '未知错误')}")

    text = result.get("result", "")
    if not text:
        raise ValueError("未识别到语音内容")

    return text
