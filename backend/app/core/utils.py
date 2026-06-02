"""通用工具函数"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional

# 中国标准时间 UTC+8
CST = timezone(timedelta(hours=8))


def cst_now() -> datetime:
    """返回当前中国标准时间（UTC+8），不含时区信息（naive datetime）"""
    return datetime.now(CST).replace(tzinfo=None)


def cst_isoformat(value: Optional[datetime]) -> Optional[str]:
    """将 naive datetime 标记为北京时间后序列化为 ISO 格式字符串（带 +08:00 后缀）"""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=CST)
    return value.isoformat()
