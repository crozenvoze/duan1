"""Trang thử nghiệm chiến lược MA/RSI, Markowitz và VaR/CVaR."""

from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import STANDARD_PRICE_LIMITS, efficient_frontier, fee_sensitivity, optimize_markowitz, portfolio_risk, run_backtest
from src.journal import read_and_calculate
from src.market_data import fetch_history, fetch_index_history
from src.sheets import read_trades

st.set_page_config(page_title="Backtest & Risk", page_icon="⚖️", layout="wide")


@st.cache_data(ttl=900, show_spinner="Đang tải dữ liệu thị trường...")
def load_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Cache OHLCV 15 phút cho ticker và khoảng ngày đã chọn."""
    return fetch_history(ticker, start, end)


st.title("⚖️ Backtest & Risk")
st.caption("Mô phỏng học tập; kết quả phụ thuộc chất lượng dữ liệu, phí, trượt giá và giả định khớp lệnh.")

with st.sidebar:
    symbol = st.text_input("Mã cổ phiếu", value="FPT", max_chars=3).strip().upper()
    end_date = st.date_input("Ngày kết thúc", value=date.today())
    start_date = st.date_input("Ngày bắt đầu", value=end_date - timedelta(days=730))
    strategy = st.selectbox("Chiến lược", ["ma_cross", "rsi"], format_func=lambda value: "MA crossover" if value == "ma_cross" else "RSI")
    exchange = st.selectbox("Sàn giao dịch", ["HOSE", "HNX", "UPCOM"])
    fast_window = st.number_input("MA nhanh", min_value=2, max_value=100, value=20)
    slow_window = st.number_input("MA chậm", min_value=3, max_value=250, value=50)
    rsi_period = st.number_input("RSI period", min_value=2, max_value=50, value=14)
    fee_bps = st.number_input("Phí mỗi chiều (bps)", min_value=0.0, max_value=500.0, value=15.0, step=1.0)
    slippage_bps = st.number_input("Trượt giá mỗi chiều (bps)", min_value=0.0, max_value=500.0, value=10.0, step=1.0)
    capital = st.number_input("Vốn ban đầu (VND)", min_value=1_000_000, value=100_000_000, step=10_000_000)
    risk_free = st.number_input("Lãi suất phi rủi ro năm (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.25) / 100

if st.button("Chạy backtest", type="primary"):
    if len(symbol) != 3 or not symbol.isalpha() or start_date >= end_date:
        st.error("Kiểm tra mã 3 chữ cái và khoảng ngày.")
    else:
        try:
            prices = load_history(symbol, start_date.isoformat(), end_date.isoformat())
            prices["exchange"] = exchange
            benchmark = None
            try:
                benchmark = fetch_index_history("VNINDEX", start_date.isoformat(), end_date.isoformat())
                if benchmark.empty:
                    benchmark = None
                    st.warning("Nguồn chưa trả dữ liệu VN-Index cho kỳ này; tiếp tục không có benchmark.")
            except Exception as benchmark_error:
                st.warning(f"Không tải được VN-Index để so sánh: {benchmark_error}")
            result = run_backtest(
                prices,
                strategy=strategy,
                fast_window=int(fast_window),
                slow_window=int(slow_window),
                rsi_period=int(rsi_period),
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                initial_capital=float(capital),
                risk_free_rate=risk_free,
                limit_pct_by_exchange=STANDARD_PRICE_LIMITS,
                benchmark_prices=benchmark,
            )
            metrics = result["metrics"]
            a, b, c, d = st.columns(4)
            a.metric("Giá trị cuối", f"{metrics['final_equity']:,.0f} VND")
            b.metric("CAGR", "—" if metrics["cagr"] is None else f"{metrics['cagr']:.2%}")
            c.metric("Sharpe", "—" if metrics["sharpe"] is None else f"{metrics['sharpe']:.2f}")
            d.metric("Max drawdown", f"{metrics['max_drawdown_pct']:.2%}" if metrics["max_drawdown_pct"] is not None else "—")
            st.write(f"Buy-and-hold cùng khoảng: **{metrics['buy_and_hold_return']:.2%}** · Win rate giao dịch đóng: **{metrics['win_rate'] if metrics['win_rate'] is not None else float('nan'):.2%}**")
            if "benchmark_return" in metrics:
                st.write(
                    f"Trong phiên giao dịch trùng nhau — chiến lược: **{metrics['strategy_return_on_benchmark_window']:.2%}** · "
                    f"VN-Index: **{metrics['benchmark_return']:.2%}** · chênh lệch: **{metrics['benchmark_excess_return']:.2%}**"
                )

            fig = go.Figure()
            curve = result["equity_curve"]
            fig.add_trace(go.Scatter(x=curve["date"], y=curve["equity"], mode="lines", name="Chiến lược"))
            normalized_buy_hold = prices["close"] / prices["close"].iloc[0] * capital
            fig.add_trace(go.Scatter(x=prices["date"], y=normalized_buy_hold, mode="lines", name="Buy-and-hold"))
            if not result["benchmark_curve"].empty:
                benchmark_curve = result["benchmark_curve"]
                fig.add_trace(go.Scatter(x=benchmark_curve["date"], y=benchmark_curve["benchmark_normalized"], mode="lines", name="VN-Index"))
            fig.update_layout(title="Đường vốn", yaxis_title="VND", height=420)
            st.plotly_chart(fig, width="stretch")
            st.dataframe(result["trades"], hide_index=True, width="stretch")
            st.markdown("**Giả định và hạn chế**")
            for assumption in result["assumptions"]:
                st.write(f"- {assumption}")
            st.markdown("**Độ nhạy theo phí giao dịch**")
            sensitivity = fee_sensitivity(
                prices,
                [0, 5, 10, 15, 20, 30],
                strategy=strategy,
                fast_window=int(fast_window),
                slow_window=int(slow_window),
                rsi_period=int(rsi_period),
                slippage_bps=slippage_bps,
                initial_capital=float(capital),
                risk_free_rate=risk_free,
                limit_pct_by_exchange=STANDARD_PRICE_LIMITS,
            )
            st.dataframe(sensitivity, hide_index=True, width="stretch")
            st.caption("Biên độ giá mặc định cho ngày giao dịch thông thường: HOSE ±7%, HNX ±10%, UPCoM ±15%; cần kiểm tra trường hợp đặc biệt trước khi diễn giải.")
        except Exception as exc:
            st.error(f"Không chạy được backtest: {exc}")

st.divider()
st.subheader("VaR và CVaR danh mục")
st.caption("Danh mục lấy từ các vị thế mở trong Trading Journal; giá trị ước tính dùng close mới nhất.")
if st.button("Tính VaR/CVaR"):
    try:
        journal = read_and_calculate(read_trades())
        holdings = {ticker: int(position["quantity"]) for ticker, position in journal["positions"].items() if position["quantity"] > 0}
        if not holdings:
            st.error("Trading Journal chưa có vị thế mở để tính VaR/CVaR.")
        else:
            end = date.today()
            start = end - timedelta(days=400)
            returns = []
            market_values = {}
            for ticker, quantity in holdings.items():
                frame = load_history(ticker, start.isoformat(), end.isoformat())
                market_values[ticker] = quantity * float(frame["close"].iloc[-1])
                returns.append(frame.set_index("date")["close"].pct_change().rename(ticker))
            return_frame = pd.concat(returns, axis=1).dropna()
            weights = pd.Series(market_values) / sum(market_values.values())
            weighted_returns = return_frame[weights.index].mul(weights, axis=1).sum(axis=1)
            portfolio_value = sum(market_values.values())
            result = portfolio_risk(weighted_returns, portfolio_value)
            st.write(f"Giá trị danh mục ước tính theo close gần nhất: **{portfolio_value:,.0f} VND**")
            st.dataframe(pd.DataFrame(result).T.rename(columns={"VaR": "VaR (VND)", "CVaR": "CVaR (VND)"}), width="stretch")
            st.caption("Parametric và Monte Carlo giả định phân phối chuẩn; vị thế/giá được ước tính từ nhật ký và close gần nhất.")
    except Exception as exc:
        st.error(f"Không tính được VaR/CVaR: {exc}")

st.divider()
st.subheader("Markowitz")
st.caption("Tối ưu tỷ trọng long-only với giới hạn từng mã; dùng lợi suất ngày và năm hóa 252 phiên.")
markowitz_symbols = st.text_input("Mã Markowitz (>=3 mã, dấu phẩy)", value="FPT,MWG,VCB")
objective_label = st.selectbox("Mục tiêu", ["max_sharpe", "min_variance"], format_func=lambda value: "Sharpe tối đa" if value == "max_sharpe" else "Phương sai tối thiểu")
max_weight = st.slider("Tỷ trọng tối đa mỗi mã", min_value=0.2, max_value=1.0, value=0.5, step=0.05)
if st.button("Tối ưu danh mục"):
    symbols = list(dict.fromkeys(item.strip().upper() for item in markowitz_symbols.split(",") if item.strip()))
    try:
        end = date.today()
        start = end - timedelta(days=730)
        daily_returns = []
        for ticker in symbols:
            frame = load_history(ticker, start.isoformat(), end.isoformat())
            daily_returns.append(frame.set_index("date")["close"].pct_change().rename(ticker))
        return_frame = pd.concat(daily_returns, axis=1)
        result = optimize_markowitz(return_frame, objective=objective_label, risk_free_rate=risk_free, max_weight=max_weight)
        st.dataframe(pd.DataFrame({"Mã": result["weights"].keys(), "Tỷ trọng": result["weights"].values()}), hide_index=True)
        st.write(f"Lợi suất kỳ vọng năm: {result['annual_return']:.2%} · Biến động năm: {result['annual_volatility']:.2%} · Sharpe: {result['sharpe']:.2f}")
        frontier = efficient_frontier(return_frame, max_weight=max_weight)
        frontier_chart = go.Figure(go.Scatter(x=frontier["annual_volatility"], y=frontier["annual_return"], mode="lines+markers", name="Đường biên hiệu quả"))
        frontier_chart.update_layout(title="Đường biên hiệu quả", xaxis_title="Biến động năm hóa", yaxis_title="Lợi suất kỳ vọng năm hóa", height=360)
        st.plotly_chart(frontier_chart, width="stretch")
        st.caption("Kết quả nhạy với giai đoạn dữ liệu và không bảo đảm hiệu suất tương lai.")
    except Exception as exc:
        st.error(f"Không tối ưu được danh mục: {exc}")
