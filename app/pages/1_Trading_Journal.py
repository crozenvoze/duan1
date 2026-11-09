"""Dashboard tiếng Việt cho nhật ký giao dịch và chỉ số hiệu quả."""

from pathlib import Path
import sys
from math import isinf

import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.journal import read_and_calculate
from src.sheets import read_trades

st.set_page_config(page_title="Trading Journal", page_icon="📒", layout="wide")


@st.cache_data(ttl=60, show_spinner="Đang tải nhật ký từ Google Sheets...")
def load_journal() -> dict:
    """Đọc dữ liệu Sheets và tính các chỉ số; cache trong 60 giây."""
    return read_and_calculate(read_trades())


def format_vnd(value: float | int | None) -> str:
    """Định dạng giá trị tiền theo VND, làm tròn đến đồng gần nhất."""
    if value is None:
        return "—"
    return f"{value:,.0f} VND"


def format_percent(value: float | None) -> str:
    """Định dạng tỷ lệ thành phần trăm với hai chữ số thập phân."""
    return "—" if value is None else f"{value:.2%}"


st.title("📒 Trading Journal")
st.caption("Vị thế và kết quả được tính theo giá vốn bình quân gia quyền.")

refresh_col, note_col = st.columns([1, 5])
with refresh_col:
    if st.button("Làm mới dữ liệu", width="stretch"):
        load_journal.clear()
with note_col:
    st.caption("Dữ liệu được cache tối đa 60 giây; dùng nút làm mới để đọc lại ngay.")

try:
    result = load_journal()
except FileNotFoundError:
    st.error("Không tìm thấy file credentials Google. Kiểm tra cấu hình kết nối trong Step 0.3.")
    st.stop()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()
except Exception:
    st.error("Không tải được nhật ký. Kiểm tra kết nối Google Sheets, quyền truy cập và cấu trúc tab Trades.")
    st.stop()

summary = result["summary"]
positions = result["positions"]
realized = result["realized_events"]

if not positions and not realized:
    st.info("Chưa có giao dịch trong tab Trades. Thêm giao dịch rồi bấm Làm mới dữ liệu.")
    st.stop()

closed_pf = summary["closed_trade_profit_factor"]
closed_pf_text = "∞" if closed_pf is not None and isinf(closed_pf) else (
    "—" if closed_pf is None else f"{closed_pf:.2f}"
)
metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Lãi/lỗ đã thực hiện", format_vnd(summary["realized_pnl"]))
metric2.metric("Vị thế đã đóng", f"{summary['closed_trade_count']:,}")
metric3.metric("Win rate / vị thế đóng", format_percent(summary["closed_trade_win_rate"]))
metric4.metric("Profit factor / vị thế đóng", closed_pf_text)

metric5, metric6, metric7, metric8 = st.columns(4)
metric5.metric("Expectancy / vị thế đóng", format_vnd(summary["closed_trade_expectancy"]))
metric6.metric("Lãi trung bình / vị thế", format_vnd(summary["closed_trade_average_win"]))
metric7.metric("Lỗ trung bình / vị thế", format_vnd(summary["closed_trade_average_loss"]))
metric8.metric("Max drawdown / vị thế đóng", format_vnd(summary["closed_trade_max_drawdown_amount"]))

with st.expander("Thống kê theo từng lần bán (bao gồm cả bán một phần)"):
    event_pf = summary["profit_factor"]
    event_pf_text = "∞" if event_pf is not None and isinf(event_pf) else (
        "—" if event_pf is None else f"{event_pf:.2f}"
    )
    event1, event2, event3, event4 = st.columns(4)
    event1.metric("Sự kiện bán", f"{summary['closed_sell_events']:,}")
    event2.metric("Win rate / lần bán", format_percent(summary["win_rate"]))
    event3.metric("Profit factor / lần bán", event_pf_text)
    event4.metric("Expectancy / lần bán", format_vnd(summary["expectancy"]))
    st.caption("Các số liệu này xem mỗi lần bán là một sự kiện riêng; chúng có thể khác thống kê theo toàn bộ chu kỳ vị thế ở phía trên.")

st.subheader("Vị thế hiện tại")
position_rows = [
    {
        "Mã": ticker,
        "Khối lượng": position["quantity"],
        "Giá vốn bình quân": format_vnd(position["average_cost"]),
        "Tổng giá vốn": format_vnd(position["cost_basis"]),
    }
    for ticker, position in positions.items()
    if position["quantity"] > 0
]
if position_rows:
    st.dataframe(position_rows, hide_index=True, width="stretch")
else:
    st.write("Hiện không còn vị thế mở.")

st.subheader("Lãi/lỗ và rủi ro")
risk1, risk2, risk3, risk4 = st.columns(4)
risk1.metric("Max drawdown / lần bán", format_vnd(summary["max_drawdown_amount"]))
risk2.metric("Tỷ lệ drawdown / lần bán", format_percent(summary["max_drawdown_pct"]))
risk3.metric("R-multiple TB / lần bán", "—" if summary["average_r_multiple"] is None else f"{summary['average_r_multiple']:.2f}R")
risk4.metric("R-multiple TB / chu kỳ đóng", "—" if summary["closed_trade_average_r_multiple"] is None else f"{summary['closed_trade_average_r_multiple']:.2f}R")
st.caption("Drawdown được tính trên lãi/lỗ đã thực hiện cộng dồn từ 0; chưa gồm tiền mặt, lãi/lỗ chưa thực hiện hoặc dòng tiền nạp/rút.")

left, right = st.columns(2)
with left:
    st.markdown("#### Đường lãi/lỗ đã thực hiện")
    if result["equity_curve"]:
        curve = result["equity_curve"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(1, len(curve) + 1)),
            y=[item["cumulative_realized_pnl"] for item in curve],
            mode="lines+markers",
            name="P&L cộng dồn",
            line={"color": "#0f766e", "width": 3},
            hovertemplate="Lần bán %{x}<br>P&L cộng dồn %{y:,.0f} VND<extra></extra>",
        ))
        fig.update_layout(xaxis_title="Thứ tự sự kiện bán", yaxis_title="VND", height=350, margin={"t": 20, "b": 30})
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Chưa có lệnh bán để vẽ đường lãi/lỗ.")

with right:
    st.markdown("#### Phân bố lãi/lỗ mỗi lần bán")
    if realized:
        pnl_values = [event["realized_pnl"] for event in realized]
        colors = ["#16865c" if value >= 0 else "#c2413b" for value in pnl_values]
        fig = go.Figure(go.Bar(
            x=[f"{event['ticker']} · {index + 1}" for index, event in enumerate(realized)],
            y=pnl_values,
            marker_color=colors,
            hovertemplate="%{x}<br>%{y:,.0f} VND<extra></extra>",
        ))
        fig.update_layout(xaxis_title="Sự kiện bán", yaxis_title="VND", height=350, margin={"t": 20, "b": 50})
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Chưa có lệnh bán để vẽ phân bố lãi/lỗ.")

st.subheader("Kết quả từng lần bán")
if realized:
    realized_rows = [
        {
            "Ngày": event["trade_date"] or "—",
            "Mã": event["ticker"],
            "Khối lượng": event["quantity"],
            "Giá vốn bình quân": format_vnd(event["average_cost"]),
            "Giá bán": format_vnd(event["sell_price"]),
            "Lãi/lỗ": format_vnd(event["realized_pnl"]),
            "R-multiple": "—" if event["r_multiple"] is None else f"{event['r_multiple']:.2f}R",
            "Chiến lược": event["strategy_tag"],
        }
        for event in realized
    ]
    st.dataframe(realized_rows, hide_index=True, width="stretch")

st.subheader("Các chu kỳ vị thế đã đóng")
if result["closed_trades"]:
    closed_rows = [
        {
            "Mã": trade["ticker"],
            "Ngày mở": trade["entry_date"] or "—",
            "Ngày đóng": trade["exit_date"] or "—",
            "Số lệnh mua/bán": f"{trade['buy_events']}/{trade['sell_events']}",
            "Khối lượng mua/bán": f"{trade['shares_bought']:,}/{trade['shares_sold']:,}",
            "Lãi/lỗ toàn chu kỳ": format_vnd(trade["realized_pnl"]),
            "R-multiple": "—" if trade["r_multiple"] is None else f"{trade['r_multiple']:.2f}R",
            "Chiến lược": ", ".join(trade["strategy_tags"]) or "Chưa gắn nhãn",
        }
        for trade in result["closed_trades"]
    ]
    st.dataframe(closed_rows, hide_index=True, width="stretch")
else:
    st.info("Chưa có vị thế nào được đóng hoàn toàn. Bán một phần chưa tạo thành giao dịch đóng.")

st.subheader("Phân tích theo chiến lược")
strategy_rows = [
    {
        "Chiến lược": tag,
        "Số lần bán": values["events"],
        "Số lần thắng": values["wins"],
        "Số lần lỗ": values["losses"],
        "Win rate": format_percent(values["win_rate"]),
        "Lãi/lỗ đã thực hiện": format_vnd(values["realized_pnl"]),
    }
    for tag, values in result["by_strategy"].items()
]
if strategy_rows:
    st.dataframe(strategy_rows, hide_index=True, width="stretch")
else:
    st.write("Chưa có lệnh bán để phân tích chiến lược.")

with st.expander("Định nghĩa và giả định"):
    st.markdown(
        """
        - **Giá vốn bình quân:** tổng giá mua cộng phí mua, chia tổng số cổ phiếu đang giữ.
        - **Lãi/lỗ đã thực hiện:** giá bán × khối lượng − giá vốn phân bổ − phí bán.
        - **Giao dịch đã đóng:** một chu kỳ bắt đầu ở lần mua đầu tiên sau khi vị thế bằng 0 và kết thúc khi bán hết. Mua thêm hoặc bán một phần vẫn thuộc cùng chu kỳ.
        - **Win rate / profit factor / expectancy chính:** tính trên lãi/lỗ gộp của từng chu kỳ vị thế đã đóng; expectancy = xác suất thắng × lãi trung bình − xác suất lỗ × lỗ trung bình. Vị thế còn mở không được tính vào các chỉ số này.
        - **Thống kê theo lần bán:** mỗi lần bán là một sự kiện riêng và được trình bày trong phần mở rộng để đối chiếu; có thể khác thống kê theo chu kỳ.
        - **R-multiple:** lãi/lỗ sự kiện bán / rủi ro ban đầu phân bổ cho số cổ phiếu bán. Stop loss khai ở lệnh mua được kế thừa và phân bổ bình quân theo vị thế còn lại; dữ liệu cũ có stop loss trên lệnh bán vẫn được hỗ trợ.
        - **R-multiple toàn chu kỳ:** tổng lãi/lỗ đã thực hiện trong chu kỳ / tổng rủi ro ban đầu đã phân bổ cho các lần bán. Với dữ liệu mới, nên nhập stop loss ở từng lệnh mua để rủi ro ban đầu phản ánh đúng kế hoạch.
        - Bán khống, giá hiện tại và lãi/lỗ chưa thực hiện chưa được tính. Drawdown hiện dùng P&L đã thực hiện cộng dồn từ 0, không phải NAV đầy đủ có tiền mặt.
        """
    )
