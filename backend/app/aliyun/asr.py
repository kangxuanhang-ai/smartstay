import json
import time
import uuid
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timezone

import httpx

from app.core.config import settings


# 阿里云智能语音交互 REST API
# https://help.aliyun.com/document_detail/324242.html

NLS_TOKEN_URL = "https://nls-meta.cn-shanghai.aliyuncs.com/"
NLS_GATEWAY_URL = "https://nls-gateway.cn-shanghai.aliyuncs.com/ws/v1"


async def _get_token() -> str:
    """获取阿里云 NLS Token"""
    params = {
        "AccessKeyId": settings.ALIYUN_ACCESS_KEY_ID,
        "Action": "CreateToken",
        "Format": "JSON",
        "RegionId": settings.ALIYUN_REGION_ID,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2019-02-28",
    }

    # 按字典序排序
    sorted_params = sorted(params.items())
    query_string = urllib.parse.urlencode(sorted_params, quote_via=urllib.parse.quote)
    string_to_sign = f"GET&%2F&{urllib.parse.quote(query_string, safe='')}"

    # HMAC-SHA1 签名
    sign_key = settings.ALIYUN_ACCESS_KEY_SECRET + "&"
    signature = base64.b64encode(
        hmac.new(sign_key.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()

    params["Signature"] = signature

    async with httpx.AsyncClient() as client:
        resp = await client.get(NLS_TOKEN_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("Token", {}).get("Id")
        if not token:
            raise Exception(f"获取 Token 失败: {data}")
        return token


async def recognize_speech(audio_data: bytes, sample_rate: int = 16000) -> str:
    """
    语音识别 - 将音频转为文字

    Args:
        audio_data: 音频数据 (PCM/WAV 格式)
        sample_rate: 采样率，默认 16000

    Returns:
        识别出的文字，如果识别失败返回空字符串
    """
    token = await _get_token()

    # 构建请求
    request_payload = {
        "appkey": "",  # 不需要 appkey，用 token 认证
        "token": token,
        "format": "wav",
        "sample_rate": sample_rate,
        "enable_punctuation_prediction": True,
        "enable_inverse_text_normalization": True,
    }

    # 使用 REST API 提交录音文件识别请求
    headers = {
        "Content-Type": "application/octet-stream",
        "X-NLS-Token": token,
    }

    # 方式一：实时语音识别（直接发送音频流）
    # 简化实现：使用一句话识别
    api_url = f"{NLS_GATEWAY_URL}/api"

    payload = {
        "header": {
            "message_id": str(uuid.uuid4()),
            "namespace": "FlowingSpeechRecognizer",
            "name": "Start",
            "appkey": "",
        },
        "payload": {
            "format": "wav",
            "sample_rate": sample_rate,
            "enable_intermediate_result": False,
        },
        "context": {
            "device": {
                "uuid": str(uuid.uuid4()),
            },
        },
    }

    # 简化方案：直接用 httpx 调用一句话识别 REST API
    # 阿里云 NLS 一句话识别 API
    rest_url = "https://nls-gateway.cn-shanghai.aliyuncs.com/streaming/v1/asr"

    params = {
        "appkey": settings.ALIYUN_ACCESS_KEY_ID,  # 使用 access key 作为标识
    }

    headers = {
        "Content-Type": "application/octet-stream",
        "X-NLS-Token": token,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                rest_url,
                params=params,
                content=audio_data,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()

            # 解析结果
            if result.get("status") == 20000000:
                text = result.get("result", "")
                return text
            else:
                # 识别失败
                return ""
    except httpx.TimeoutException:
        raise Exception("语音识别超时")
    except httpx.HTTPStatusError as e:
        raise Exception(f"语音识别服务错误: {e.response.status_code}")
    except Exception as e:
        raise Exception(f"语音识别失败: {str(e)}")
