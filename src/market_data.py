"""Lớp lấy dữ liệu thị trường, chuẩn hóa OHLCV và cache cục bộ.

Vnstock được nạp trễ để người dùng vẫn chạy journal khi chưa cài hoặc đăng ký
nguồn dữ liệu thị trường. API Unified UI v4+ dùng Market().equity.ohlcv().
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, TypeVar

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / ".cache" / "market_data"
T = TypeVar("T")


def _retry(operation: Callable[[], T], attempts: int = 3) -> T:
    """Thử lại lỗi nguồn mạng tối đa ba lần với thời gian chờ tăng dần."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:  # API nguồn dữ liệu có thể phát sinh nhiều loại lỗi.
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.7 * (2 ** attempt))
    raise RuntimeError(f"Không lấy được dữ liệu sau {attempts} lần thử: {last_error}") from last_error


def _market_client() -> Any:
    """Tạo client Vnstock; báo hướng dẫn nếu gói chưa cài hoặc chưa đăng ký."""
    try:
        from vnstock import Market
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài Vnstock. Xem hướng dẫn cài và đăng ký tại https://vnstocks.com/download; "
            "API nguồn và quyền Community có thể thay đổi."
        ) from exc
    return Market()


def _normalize_history(frame: Any, symbol: str) -> pd.DataFrame:
    """Chuẩn hóa tên cột OHLCV thường gặp về date/open/high/low/close/volume."""
    if frame is None:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    result = pd.DataFrame(frame).copy()
    result.columns = [str(column).strip().lower() for column in result.columns]
    aliases = {
        "date": ("time", "trading_date", "datetime"),
        "open": ("open_price",),
        "high": ("high_price",),
        "low": ("low_price",),
        "close": ("close_price", "price_close"),
        "volume": ("total_volume", "vol"),
    }
    for canonical, alternatives in aliases.items():
        if canonical not in result.columns:
            source = next((name for name in alternatives if name in result.columns), None)
            if source:
                result = result.rename(columns={source: canonical})
    required = ["date", "open", "high", "low", "close", "volume"]
    missing = [name for name in required if name not in result.columns]
    if missing:
        raise RuntimeError(f"Nguồn Vnstock trả thiếu cột {missing} cho mã {symbol}; cần kiểm tra schema.")
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    for column in ("open", "high", "low", "close", "volume"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date", keep="last")
    result["ticker"] = symbol.upper()
    return result.reset_index(drop=True)


def fetch_history(
    symbol: str,
    start: str,
    end: str,
    *,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Lấy OHLCV theo ngày; cache CSV theo mã và khoảng ngày để giảm gọi API."""
    ticker = symbol.strip().upper()
    if len(ticker) != 3 or not ticker.isalpha():
        raise ValueError("Mã cổ phiếu phải gồm đúng ba chữ cái.")
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    if start_ts > end_ts:
        raise ValueError("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{ticker}_{start_ts:%Y%m%d}_{end_ts:%Y%m%d}.csv"
    if cache_file.exists() and not force_refresh:
        try:
            cached = pd.read_csv(cache_file, parse_dates=["date"])
            modified_at = pd.Timestamp.fromtimestamp(cache_file.stat().st_mtime)
            if not cached.empty and pd.Timestamp.now() - modified_at < pd.Timedelta(days=1):
                return cached
        except Exception:
            cache_file.unlink(missing_ok=True)

    market = _market_client()
    raw = _retry(lambda: market.equity.ohlcv(symbol=ticker, start=start_ts.strftime("%Y-%m-%d"), end=end_ts.strftime("%Y-%m-%d")))
    frame = _normalize_history(raw, ticker)
    frame = frame[(frame["date"] >= start_ts) & (frame["date"] <= end_ts)].reset_index(drop=True)
    temp_file = cache_file.with_suffix(".tmp")
    frame.to_csv(temp_file, index=False)
    temp_file.replace(cache_file)
    return frame


def get_current_price(symbol: str) -> dict[str, Any]:
    """Lấy giá gần nhất từ quote; nếu API quote lỗi thì dùng close lịch sử mới nhất."""
    ticker = symbol.strip().upper()
    try:
        market = _market_client()
        quote = _retry(lambda: market.equity.quote(symbol=ticker))
        frame = pd.DataFrame(quote)
        if not frame.empty:
            lowered = {str(col).lower(): col for col in frame.columns}
            price_col = next((lowered[name] for name in ("close", "price", "match_price", "last_price") if name in lowered), None)
            if price_col is not None:
                price = pd.to_numeric(frame[price_col], errors="coerce").dropna()
                if not price.empty:
                    return {"ticker": ticker, "price": float(price.iloc[-1]), "source": "quote"}
    except Exception:
        pass

    end = pd.Timestamp.now().strftime("%Y-%m-%d")
    start = (pd.Timestamp.now() - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    history = fetch_history(ticker, start, end)
    if history.empty:
        raise RuntimeError(f"Không có giá gần nhất cho mã {ticker}.")
    last = history.iloc[-1]
    return {"ticker": ticker, "price": float(last["close"]), "date": last["date"], "source": "historical_close"}


def list_symbols_by_industry() -> pd.DataFrame:
    """Trả bảng danh sách cổ phiếu theo ngành từ Vnstock Reference API."""
    try:
        from vnstock import Reference
    except ImportError as exc:
        raise RuntimeError("Chưa cài Vnstock Reference API.") from exc
    reference = Reference()
    return pd.DataFrame(_retry(lambda: reference.equity.list_by_industry()))
