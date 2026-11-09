"""Cập nhật cache OHLCV của các mã trong Watchlist lên Google Sheets."""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from src.market_data import fetch_history
from src.sheets import read_worksheet, upsert_prices_cache


def watchlist_tickers(rows: list[list[str]]) -> list[str]:
    """Lấy danh sách mã hợp lệ từ bảng Watchlist; bỏ qua dòng trống/sai mã."""
    if not rows:
        return []
    headers = [cell.strip().lower() for cell in rows[0]]
    if "ticker" not in headers:
        raise RuntimeError("Tab Watchlist thiếu cột ticker.")
    index = headers.index("ticker")
    tickers = {
        row[index].strip().upper()
        for row in rows[1:]
        if len(row) > index and len(row[index].strip()) == 3 and row[index].strip().isalpha()
    }
    return sorted(tickers)


def update_watchlist_prices(*, lookback_days: int = 45) -> tuple[int, int, int]:
    """Tải OHLCV 45 ngày gần nhất cho Watchlist rồi upsert vào Prices_Cache.

    Trả về (số mã cập nhật thành công, số dòng thêm, số dòng cập nhật). Lỗi
    từng mã được tổng hợp và nêu tên mã cùng loại lỗi, không in thông tin bí mật.
    """
    rows = read_worksheet("Watchlist")
    tickers = watchlist_tickers(rows)
    if not tickers:
        print("Watchlist chưa có mã hợp lệ; không có dữ liệu để cập nhật.")
        return 0, 0, 0

    today = pd.Timestamp.now(tz=ZoneInfo("Asia/Ho_Chi_Minh")).date()
    start = today - timedelta(days=lookback_days)
    records: list[dict[str, object]] = []
    errors: list[str] = []
    successful_tickers = 0

    for ticker in tickers:
        try:
            history = fetch_history(ticker, start.isoformat(), today.isoformat(), force_refresh=True)
            if history.empty:
                errors.append(f"{ticker}: không có dữ liệu")
                continue
            for item in history.itertuples(index=False):
                records.append(
                    {
                        "ticker": ticker,
                        "date": pd.Timestamp(item.date).date().isoformat(),
                        "open": float(item.open),
                        "high": float(item.high),
                        "low": float(item.low),
                        "close": float(item.close),
                        "volume": float(item.volume),
                    }
                )
            successful_tickers += 1
        except Exception as exc:
            errors.append(f"{ticker}: {type(exc).__name__}")

    added, updated = upsert_prices_cache(records)
    print(
        f"Hoàn tất cập nhật Prices_Cache: {successful_tickers}/{len(tickers)} mã; "
        f"{added} dòng thêm, {updated} dòng sửa."
    )
    if errors:
        print("Mã cần kiểm tra: " + "; ".join(errors))
        raise RuntimeError(f"Có {len(errors)} mã Watchlist chưa cập nhật được.")
    return successful_tickers, added, updated


if __name__ == "__main__":
    update_watchlist_prices()
