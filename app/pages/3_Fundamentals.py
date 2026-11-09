"""Dashboard phân tích BCTC và DuPont từ tab Fundamentals đã chuẩn hóa."""

from pathlib import Path
import sys
from math import isfinite

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
    normalize_vnstock_statements,
    receivables_growth_status,
    read_fundamentals,
    write_fundamentals,
)
from src.metrics import bank_ratios
from src.bank_fundamentals import read_bank_fundamentals, write_bank_fundamental

st.set_page_config(page_title="Fundamentals", page_icon="📊", layout="wide")


@st.cache_data(ttl=300, show_spinner="Đang đọc tab Fundamentals...")
def load_fundamentals() -> pd.DataFrame:
    """Đọc bảng fundamentals, cache 5 phút để hạn chế gọi Sheets."""
    return read_fundamentals()


@st.cache_data(ttl=300, show_spinner="Đang đọc lịch sử chỉ số ngân hàng...")
def load_bank_fundamentals() -> pd.DataFrame:
    """Đọc lịch sử riêng cho ngân hàng và cache trong 5 phút."""
    return read_bank_fundamentals()


st.title("📊 Fundamental Dashboard")
st.caption("Chỉ tính từ dữ liệu đã ánh xạ rõ sang chỉ tiêu VAS; ngân hàng cần nhánh phân tích riêng.")

try:
    data = load_fundamentals()
except Exception:
    st.error("Không đọc được tab Fundamentals. Kiểm tra kết nối Google Sheets.")
    st.stop()

with st.expander("Phân tích riêng ngân hàng"):
    st.caption(
        "Nhập số liệu đã đối chiếu từ BCTC và thuyết minh. Các khoản mục nợ xấu, CASA và tài sản sinh lãi "
        "có thể cần thuyết minh; ô trống được để là chưa đủ dữ liệu."
    )
    with st.form("bank_ratio_form"):
        left, right = st.columns(2)
        with left:
            bank_symbol = st.text_input("Mã ngân hàng", max_chars=3, placeholder="VCB").strip().upper()
            bank_period = st.text_input("Kỳ báo cáo", placeholder="2025-Q4 hoặc 2025")
            nii_ttm = st.text_input("Thu nhập lãi thuần TTM (VND)", placeholder="Ví dụ: 50000000000")
            earning_assets = st.text_input("Tài sản sinh lãi bình quân (VND)", placeholder="Bình quân theo kỳ")
            operating_expenses = st.text_input("Chi phí hoạt động (VND)", placeholder="Có thể nhập số âm")
            operating_income = st.text_input("Tổng thu nhập hoạt động (VND)")
            npl_balance = st.text_input("Nợ nhóm 3–5 (VND)")
        with right:
            gross_loans = st.text_input("Dư nợ cho vay gộp (VND)")
            demand_deposits = st.text_input("Tiền gửi không kỳ hạn (VND)")
            escrow_deposits = st.text_input("Tiền ký quỹ (VND)")
            dedicated_deposits = st.text_input("Vốn chuyên dùng (VND)")
            customer_deposits = st.text_input("Tiền gửi khách hàng (VND)")
            provision_ttm = st.text_input("Chi phí dự phòng tín dụng TTM (VND)", placeholder="Có thể nhập số âm")
            average_gross_loans = st.text_input("Dư nợ cho vay gộp bình quân (VND)")
            source_note = st.text_input("Nguồn/ghi chú đối chiếu", placeholder="Tên báo cáo, trang, đường dẫn...")
        save_record = st.checkbox("Lưu bản ghi vào tab Bank_Fundamentals")
        submitted = st.form_submit_button("Tính chỉ số ngân hàng")
    if submitted:
        if len(bank_symbol) != 3 or not bank_symbol.isalpha():
            st.error("Nhập mã ngân hàng gồm đúng 3 chữ cái.")
        else:
            def parse_amount(value: str) -> float | None:
                if not value.strip():
                    return None
                amount = float(value.replace(",", "").replace(" ", ""))
                if not isfinite(amount):
                    raise ValueError("số tiền phải là số hữu hạn")
                return amount

            try:
                bank_values = bank_ratios(
                    net_interest_income_ttm=parse_amount(nii_ttm),
                    average_interest_earning_assets=parse_amount(earning_assets),
                    operating_expenses=parse_amount(operating_expenses),
                    operating_income=parse_amount(operating_income),
                    non_performing_loans=parse_amount(npl_balance),
                    gross_customer_loans=parse_amount(gross_loans),
                    demand_deposits=parse_amount(demand_deposits),
                    margin_escrow_deposits=parse_amount(escrow_deposits),
                    dedicated_deposits=parse_amount(dedicated_deposits),
                    customer_deposits=parse_amount(customer_deposits),
                    credit_loss_provision_ttm=parse_amount(provision_ttm),
                    average_gross_customer_loans=parse_amount(average_gross_loans),
                )
                if save_record:
                    write_bank_fundamental({
                        "ticker": bank_symbol,
                        "period": bank_period,
                        "net_interest_income_ttm": parse_amount(nii_ttm),
                        "average_interest_earning_assets": parse_amount(earning_assets),
                        "operating_expenses": parse_amount(operating_expenses),
                        "operating_income": parse_amount(operating_income),
                        "non_performing_loans": parse_amount(npl_balance),
                        "gross_customer_loans": parse_amount(gross_loans),
                        "demand_deposits": parse_amount(demand_deposits),
                        "margin_escrow_deposits": parse_amount(escrow_deposits),
                        "dedicated_deposits": parse_amount(dedicated_deposits),
                        "customer_deposits": parse_amount(customer_deposits),
                        "credit_loss_provision_ttm": parse_amount(provision_ttm),
                        "average_gross_customer_loans": parse_amount(average_gross_loans),
                        **bank_values,
                        "source_note": source_note.strip(),
                    })
                    load_bank_fundamentals.clear()
                    st.success(f"Đã thêm bản ghi {bank_symbol} kỳ {bank_period} vào Bank_Fundamentals.")
                st.markdown(f"**{bank_symbol} · Chỉ số ngân hàng**")
                labels = (
                    ("nim", "NIM"), ("cir", "CIR"), ("npl", "NPL"),
                    ("ldr", "LDR phân tích"), ("casa", "CASA"), ("provision_to_loans", "Dự phòng / dư nợ"),
                )
                columns = st.columns(len(labels))
                for column, (key, label) in zip(columns, labels):
                    value = bank_values[key]
                    column.metric(label, "—" if value is None else f"{value:.2%}")
                st.caption(
                    "CIR và tỷ lệ dự phòng hiển thị dạng dương bằng trị tuyệt đối chi phí. "
                    "LDR ở đây là dư nợ gộp / tiền gửi khách hàng, không phải tỷ lệ quy định của NHNN."
                )
            except ValueError as exc:
                st.error(f"Dữ liệu nhập chưa hợp lệ: {exc}")
            except Exception as exc:
                st.error(f"Không thể lưu dữ liệu ngân hàng vào Google Sheets: {exc}")

with st.expander("Lịch sử chỉ số ngân hàng đã lưu"):
    try:
        bank_history = load_bank_fundamentals()
        if bank_history.empty:
            st.info("Chưa có bản ghi trong tab Bank_Fundamentals.")
        else:
            st.dataframe(
                bank_history.sort_values("saved_at", ascending=False),
                hide_index=True,
                use_container_width=True,
            )
    except Exception:
        st.error("Không đọc được lịch sử Bank_Fundamentals trong Google Sheets.")

with st.expander("Lấy, ánh xạ và lưu BCTC Vnstock", expanded=data.empty):
    st.caption(
        "Ứng dụng dùng mã VAS ổn định cho các chỉ tiêu đã biết. Bạn cần chọn rõ hai mã khoản vay "
        "trong bảng cân đối trước khi tính và lưu; không dùng tổng nợ phải trả thay nợ vay."
    )
    fetch_col, period_col = st.columns([2, 1])
    with fetch_col:
        ticker_raw = st.text_input("Mã cổ phiếu", max_chars=3, placeholder="FPT", key="fundamental_fetch_ticker").strip().upper()
    with period_col:
        period_type = st.selectbox(
            "Kỳ lấy dữ liệu", ["quarter", "year"],
            format_func=lambda value: "Quý" if value == "quarter" else "Năm",
            key="fundamental_fetch_period",
        )
    if st.button("Lấy báo cáo từ Vnstock", key="fetch_fundamental_statements"):
        if len(ticker_raw) != 3 or not ticker_raw.isalpha():
            st.error("Nhập mã gồm đúng 3 chữ cái.")
        else:
            try:
                st.session_state["fundamental_raw"] = fetch_raw_statements(ticker_raw, period_type)
                st.session_state["fundamental_raw_ticker"] = ticker_raw
                st.session_state["fundamental_raw_period"] = period_type
            except Exception as exc:
                st.error(str(exc))

    raw = st.session_state.get("fundamental_raw")
    if raw:
        for name, frame in raw.items():
            st.markdown(f"**{name}**")
            st.dataframe(frame, use_container_width=True, hide_index=True)
        balance = raw.get("balance_sheet", pd.DataFrame())
        if not balance.empty:
            id_col = "id" if "id" in balance.columns else "item_id" if "item_id" in balance.columns else None
            name_col = "name" if "name" in balance.columns else "item_name" if "item_name" in balance.columns else None
            if id_col:
                candidates = balance[[id_col] + ([name_col] if name_col else [])].drop_duplicates().dropna(subset=[id_col])
                option_labels = {
                    str(row[id_col]): f"{row[id_col]} — {row[name_col]}" if name_col and pd.notna(row[name_col]) else str(row[id_col])
                    for _, row in candidates.iterrows()
                }
                ids = list(option_labels)
                if len(ids) < 2:
                    st.warning("Bảng cân đối cần có ít nhất hai mã để chọn khoản vay ngắn hạn và dài hạn.")
                else:
                    st.markdown("**Chọn mã khoản vay theo đúng dòng của báo cáo**")
                    short_id = st.selectbox("Vay ngắn hạn", ids, format_func=lambda value: option_labels[value], key="fundamental_short_debt_id")
                    long_options = [value for value in ids if value != short_id]
                    long_id = st.selectbox("Vay dài hạn", long_options, format_func=lambda value: option_labels[value], key="fundamental_long_debt_id")
                    industry = st.text_input("Ngành để so sánh", placeholder="Công nghệ, Bán lẻ...", key="fundamental_industry")
                    if st.button("Chuẩn hóa và lưu vào Fundamentals", key="save_fundamental_rows"):
                        try:
                            rows = normalize_vnstock_statements(
                                st.session_state["fundamental_raw_ticker"],
                                raw,
                                period_type=st.session_state["fundamental_raw_period"],
                                borrowing_ids=(short_id, long_id),
                                industry=industry.strip(),
                            )
                            if not rows:
                                st.warning("Chưa tạo được dòng nào: cần có kỳ hiện tại và kỳ liền trước, cùng đủ các chỉ tiêu bắt buộc.")
                            else:
                                count = write_fundamentals(rows)
                                load_fundamentals.clear()
                                st.success(f"Đã thêm {count} kỳ vào tab Fundamentals; các kỳ đã có không bị ghi đè.")
                        except Exception as exc:
                            st.error(f"Không thể chuẩn hóa hoặc lưu dữ liệu: {exc}")
            else:
                st.warning("Không tìm thấy cột mã VAS trong bảng cân đối; cần báo cáo dạng long của Vnstock.")

if data.empty or "ticker" not in data.columns:
    st.info("Tab Fundamentals chưa có dữ liệu chuẩn hóa. Dùng phần trên để lấy BCTC, xem mã VAS, chọn rõ khoản vay và lưu các kỳ đủ dữ liệu.")
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
