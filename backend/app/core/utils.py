"""通用工具函数"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from math import ceil
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


def calculate_nights(check_in_time, check_out_time=None):
    """计算住夜晚数。酒店惯例：入住当天算1晚。"""
    end = check_out_time or cst_now()
    delta = end - check_in_time
    seconds = delta.total_seconds()
    if seconds <= 0:
        return 1
    return max(1, ceil(seconds / 86400))
