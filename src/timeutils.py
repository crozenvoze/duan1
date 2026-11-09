"""Tiện ích về ngày hiện tại theo múi giờ thị trường Việt Nam."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def vietnam_today(now: datetime | None = None) -> date:
    """Trả ngày lịch tại Việt Nam, kể cả khi máy chủ đang chạy theo UTC.

    Đầu vào tùy chọn là một datetime có múi giờ để kiểm thử hoặc tái sử dụng.
    Đầu ra là ngày địa phương `Asia/Ho_Chi_Minh`; datetime không múi giờ bị từ chối.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now phải là datetime có thông tin múi giờ.")
    return current.astimezone(VIETNAM_TIMEZONE).date()
