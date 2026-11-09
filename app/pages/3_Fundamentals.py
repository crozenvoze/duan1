"""Dashboard phân tích BCTC và DuPont từ tab Fundamentals đã chuẩn hóa."""

from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fundamentals import (
    calculate_fundamental_row,
    cash_conversion_quality_status,
    fetch_raw_statements,
    receivables_growth_status,
    read_fundamentals,
)

st.set_page_config(page_title="Fundamentals", page_icon="📊", layout="wide")


@st.cache_data(ttl=300, show_spinner="Đang đọc tab Fundamentals...")
def load_fundamentals() -> pd.DataFrame:
    """Đọc bảng fundamentals, cache 5 phút để hạn chế gọi Sheets."""
    return read_fundamentals()


st.title("📊 Fundamental Dashboard")
st.caption("Chỉ tính từ dữ liệu đã ánh xạ rõ sang chỉ tiêu VAS; ngân hàng cần nhánh phân tích riêng.")

try:
    data = load_fundamentals()
except Exception:
    st.error("Không đọc được tab Fundamentals. Kiểm tra kết nối Google Sheets.")
    st.stop()

if data.empty or "ticker" not in data.columns:
    st.info("Tab Fundamentals chưa có dữ liệu chuẩn hóa. Chưa tự ánh xạ nhãn báo cáo vì schema nguồn Vnstock phụ thuộc nguồn/kỳ.")
    ticker_raw = st.text_input("Mã cần xem báo cáo thô", max_chars=3, placeholder="FPT").strip().upper()
    period = st.selectbox("Kỳ báo cáo", ["quarter", "year"], format_func=lambda value: "Quý" if value == "quarter" else "Năm")
    if st.button("Lấy báo cáo thô từ Vnstock"):
        if len(ticker_raw) != 3 or not ticker_raw.isalpha():
            st.error("Nhập mã gồm đúng 3 chữ cái.")
        else:
            try:
                raw = fetch_raw_statements(ticker_raw, period)
                for name, frame in raw.items():
                    st.markdown(f"#### {name}")
                    st.dataframe(frame, use_container_width=True)
                st.warning("Đối chiếu nhãn báo cáo với VAS và schema nội bộ trước khi ghi chỉ số.")
            except Exception as exc:
                st.error(str(exc))
    st.stop()

symbols = sorted(data["ticker"].dropna().astype(str).str.upper().unique())
ticker = st.selectbox("Chọn mã", symbols)
selected = data[data["ticker"].astype(str).str.upper() == ticker].copy()
if "period" in selected.columns:
    selected = selected.sort_values("period")

st.subheader(f"Chỉ số theo kỳ — {ticker}")
try:
    metric_rows = [calculate_fundamental_row(row) for row in selected.to_dict(orient="records")]
    metrics = pd.DataFrame(metric_rows)
except Exception as exc:
    st.error(f"Không thể tính chỉ số: {exc}")
    st.stop()

latest = metrics.iloc[-1]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Doanh thu thuần", f"{float(latest['revenue']):,.0f} VND")
col2.metric("Biên lợi nhuận ròng", "—" if pd.isna(latest["net_margin"]) else f"{latest['net_margin']:.2%}")
col3.metric("ROE", "—" if pd.isna(latest["roe_direct"]) else f"{latest['roe_direct']:.2%}")
col4.metric("Cash conversion", "—" if pd.isna(latest["cash_conversion"]) else f"{latest['cash_conversion']:.2f}x")

st.subheader("Xu hướng doanh thu và sinh lời")
left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=metrics["period"], y=metrics["revenue"], mode="lines+markers", name="Doanh thu thuần"
    ))
    fig.update_layout(title="Doanh thu thuần theo kỳ", yaxis_title="VND", height=340)
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = go.Figure()
    for column, label in (("net_margin", "Biên ròng"), ("roe_direct", "ROE"), ("roa", "ROA")):
        if column in metrics:
            fig.add_trace(go.Scatter(x=metrics["period"], y=metrics[column] * 100, mode="lines+markers", name=label))
    fig.update_layout(title="Biên lợi nhuận, ROE và ROA", yaxis_title="%", height=340)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("DuPont 3 bước")
fig = go.Figure()
for column, label in (("net_margin", "Net margin"), ("asset_turnover", "Asset turnover"), ("equity_multiplier", "Equity multiplier")):
    if column in metrics:
        fig.add_trace(go.Bar(x=metrics["period"], y=metrics[column], name=label))
fig.update_layout(title="Các thành phần DuPont theo kỳ", barmode="group", height=360)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Bảng chỉ số và đối chiếu DuPont")
display_columns = [column for column in (
    "period", "revenue", "net_income", "net_margin", "asset_turnover", "equity_multiplier",
    "roe_direct", "roe_dupont", "roa", "debt_to_equity", "cash_conversion",
) if column in metrics.columns]
st.dataframe(metrics[display_columns], hide_index=True, use_container_width=True)
industry_value = latest.get("industry", "")
industry = "" if pd.isna(industry_value) else str(industry_value).strip()
if industry and "industry" in data.columns:
    peers = data[
        (data["industry"].astype(str).str.strip() == industry)
        & (data["ticker"].astype(str).str.upper() != ticker)
        & (data["period"].astype(str) == str(latest["period"]))
    ].drop_duplicates(subset=["ticker"])
    peer_metric_rows = []
    for peer in peers.to_dict(orient="records"):
        try:
            peer_metric_rows.append(calculate_fundamental_row(peer))
        except (TypeError, ValueError):
            continue
    peer_metrics = pd.DataFrame(peer_metric_rows)
    peer_columns = [column for column in (
        "roe_direct", "roa", "net_margin", "asset_turnover", "equity_multiplier",
        "debt_to_equity", "cash_conversion",
    ) if column in peer_metrics.columns]
    peer_medians = peer_metrics[peer_columns].apply(pd.to_numeric, errors="coerce").median().dropna() if peer_columns else pd.Series(dtype=float)
    if not peer_medians.empty:
        st.markdown(f"**Trung vị các mã cùng ngành {industry}, kỳ {latest['period']}** · {peers['ticker'].nunique()} mã so sánh")
        labels = {
            "roe_direct": "ROE", "roa": "ROA", "net_margin": "Biên lợi nhuận ròng",
            "asset_turnover": "Vòng quay tài sản", "equity_multiplier": "Đòn bẩy vốn chủ",
            "debt_to_equity": "Nợ vay / vốn chủ", "cash_conversion": "CFO / lợi nhuận ròng",
        }
        peer_frame = peer_medians.rename("Trung vị ngành").rename_axis("Chỉ tiêu").reset_index()
        peer_frame["Chỉ tiêu"] = peer_frame["Chỉ tiêu"].map(labels).fillna(peer_frame["Chỉ tiêu"])
        ratio_labels = {"ROE", "ROA", "Biên lợi nhuận ròng"}
        peer_frame["Trung vị ngành"] = peer_frame.apply(
            lambda row: f"{row['Trung vị ngành']:.2%}" if row["Chỉ tiêu"] in ratio_labels
            else f"{row['Trung vị ngành']:.2f}x",
            axis=1,
        )
        st.dataframe(peer_frame, hide_index=True, use_container_width=True)
    else:
        st.info(f"Chưa có dữ liệu đã ánh xạ của mã khác cùng ngành {industry} trong kỳ {latest['period']}.")
else:
    st.info("So sánh trung vị ngành cần lưu thêm ngành, kỳ báo cáo và dữ liệu đã ánh xạ của ít nhất một mã cùng ngành khác.")

with st.expander("Chất lượng lợi nhuận — giới hạn dữ liệu hiện có"):
    status, message = cash_conversion_quality_status(
        metrics["cash_conversion"].tolist(), metrics["net_income"].tolist()
    )
    if status == "warning":
        st.warning(message)
    elif status == "info":
        st.info(message)
    elif status == "ok":
        st.success(message)
    else:
        st.info(message)
    receivables_status, receivables_message = receivables_growth_status(
        selected.to_dict(orient="records")
    )
    if receivables_status == "warning":
        st.warning(receivables_message)
    elif receivables_status == "ok":
        st.success(receivables_message)
    else:
        st.info(receivables_message)
    st.caption(
        "Quy ước cảnh báo: CFO/NI < 1 trong ít nhất 2 kỳ liên tiếp; đây là tín hiệu rà soát, không phải kết luận sai phạm. "
        "So sánh phải thu dùng cùng kỳ năm trước; revenue phải được ánh xạ nhất quán và receivables_ending là số dư cuối kỳ."
    )
