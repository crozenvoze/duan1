"""Các phép tính Watchlist thuần, tách khỏi giao diện và nguồn dữ liệu."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def price_change_from_sessions(
    closes: Sequence[float], current_price: float, sessions_back: int
) -> float | None:
    """Tính % thay đổi từ giá đóng cửa cách đây N phiên đến giá hiện tại.

    `closes` phải theo thứ tự thời gian và gồm cả phiên gần nhất. Trả None nếu
    không đủ phiên hoặc giá gốc không dương.
    """
    if sessions_back < 1 or len(closes) <= sessions_back:
        return None
    base = float(closes[-(sessions_back + 1)])
    current = float(current_price)
    if not np.isfinite(base) or not np.isfinite(current) or base <= 0:
        return None
    return current / base - 1


def volume_vs_previous_sessions(
    volumes: Sequence[float], sessions: int = 20
) -> tuple[float | None, float | None]:
    """Trả (volume phiên mới nhất, volume/average) so với N phiên trước.

    Loại phiên mới nhất khỏi mẫu trung bình để so khối lượng phiên này với
    20 phiên trước, tránh kéo chính nó vào đường chuẩn.
    """
    if sessions < 1 or len(volumes) <= sessions:
        return None, None
    values = np.asarray(volumes, dtype=float)
    prior = values[-(sessions + 1):-1]
    latest = float(values[-1])
    prior = prior[np.isfinite(prior)]
    if prior.size == 0 or not np.isfinite(latest):
        return latest if np.isfinite(latest) else None, None
    average = float(prior.mean())
    return latest, latest / average if average > 0 else None


def threshold_alert(
    price: float, alert_above: float | None, alert_below: float | None
) -> str:
    """Trả cảnh báo khi giá chạm ngưỡng trên hoặc dưới đã cấu hình."""
    if alert_above is not None and price >= alert_above:
        return "Vượt ngưỡng trên"
    if alert_below is not None and price <= alert_below:
        return "Chạm ngưỡng dưới"
    return ""
