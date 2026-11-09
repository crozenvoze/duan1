"""Trang watchlist: giá, hiệu suất theo kỳ, thanh khoản và cảnh báo ngưỡng."""

from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.market_data import fetch_history, get_current_price
from src.sheets import read_worksheet
from src.watchlist import price_change_from_sessions, threshold_alert, volume_vs_previous_sessions

st.set_page_config(page_title="Watchlist", page_icon="👀", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def load_watchlist() -> list[dict[str, str]]:
    """Đọc danh sách mã và ngưỡng theo dõi từ tab Watchlist."""
    rows = read_worksheet("Watchlist")
    if not rows:
        return []
    headers = [cell.strip().lower() for cell in rows[0]]
    return [
        {headers[i]: row[i].strip() if i < len(row) else "" for i in range(len(headers))}
        for row in rows[1:]
        if row and any(cell.strip() for cell in row)
    ]


@st.cache_data(ttl=300, show_spinner=False)
def load_prices(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Tải OHLCV một lần và cache 5 phút cho từng mã/khoảng ngày."""
    return fetch_history(ticker, start, end)


def parse_threshold(value: str) -> float | None:
    """Chuyển ngưỡng trong Sheet thành số; ô trống hoặc sai định dạng được bỏ qua."""
    try:
        return float(value) if value.strip() else None
    except ValueError:
        return None


def build_row(item: dict[str, str], start: str, end: str) -> dict[str, object]:
    """Tính biến động ngày/tuần/tháng, volume trung bình và cảnh báo cho một mã."""
    ticker = item.get("ticker", "").strip().upper()
    history = load_prices(ticker, start, end)
    if history.empty:
        raise RuntimeError(f"Nguồn dữ liệu không trả giá lịch sử cho {ticker}.")

    closes = history["close"].dropna().astype(float).reset_index(drop=True)
    current = get_current_price(ticker)
    price = float(current["price"])

    volumes = history["volume"].dropna().astype(float)
    latest_volume, volume_ratio = volume_vs_previous_sessions(volumes.to_list(), sessions=20)
    above = parse_threshold(item.get("alert_above", ""))
    below = parse_threshold(item.get("alert_below", ""))
    alert = threshold_alert(price, above, below)

    return {
        "Mã": ticker,
        "Giá gần nhất (VND)": price,
        "Loại giá": "Giá đóng cửa gần nhất" if current.get("source") == "historical_close" else "Báo giá hiện tại",
        "% ngày": price_change_from_sessions(closes.to_list(), price, 1),
        "% tuần": price_change_from_sessions(closes.to_list(), price, 5),
        "% tháng": price_change_from_sessions(closes.to_list(), price, 21),
        "KL gần nhất": latest_volume,
        "KL / TB 20 phiên": volume_ratio,
        "Ngưỡng trên": above,
        "Ngưỡng dưới": below,
        "Cảnh báo": alert,
        "Ghi chú": item.get("note", ""),
    }


st.title("👀 Watchlist")
st.caption("Giá có thể trễ theo nguồn Vnstock; đối chiếu dữ liệu trước khi ra quyết định.")
if st.button("Làm mới Watchlist"):
    load_watchlist.clear()
    load_prices.clear()

try:
    items = load_watchlist()
    if not items:
        st.info("Tab Watchlist chưa có mã. Tạo hàng tiêu đề: ticker, alert_above, alert_below, note.")
        st.stop()
    end_date = date.today()
    start_date = end_date - timedelta(days=60)
    output = []
    errors = []
    for item in items:
        ticker = item.get("ticker", "").strip().upper()
        if not ticker:
            continue
        try:
            output.append(build_row(item, start_date.isoformat(), end_date.isoformat()))
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")
    for error in errors:
        st.warning(error)
    if output:
        frame = pd.DataFrame(output)
        change_columns = ["% ngày", "% tuần", "% tháng"]
        styled = frame.style
        for column in change_columns:
            styled = styled.map(
                lambda value: "color: #067647" if pd.notna(value) and value > 0
                else ("color: #b42318" if pd.notna(value) and value < 0 else ""),
                subset=[column],
            )
        styled = styled.map(
            lambda value: "background-color: #fff1f0; color: #b42318; font-weight: 700" if value else "",
            subset=["Cảnh báo"],
        ).format(
            {"Giá gần nhất (VND)": "{:,.0f}", "KL gần nhất": "{:,.0f}",
             **{column: "{:.2%}" for column in change_columns}, "KL / TB 20 phiên": "{:.2f}x"},
            na_rep="—",
        )
        st.dataframe(styled, hide_index=True, width="stretch")
    elif not errors:
        st.info("Chưa có mã hợp lệ trong Watchlist.")
except Exception:
    st.error("Không đọc được Watchlist. Kiểm tra quyền Google Sheets và tên tab.")
