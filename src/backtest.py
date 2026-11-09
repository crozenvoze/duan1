"""Backtest long-only cơ bản và công cụ rủi ro danh mục.

Backtest dùng OHLCV theo ngày, tín hiệu tính tại phiên t và giao dịch tại close
phiên t+1. T+2 được mô phỏng bằng cách khóa bán hai phiên sau khi mua. Muốn
kiểm tra biên độ giá, dữ liệu phải có exchange và người gọi truyền map limit_pct.
"""

from __future__ import annotations

from math import sqrt
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.optimize import linprog
from scipy.stats import norm

from src.metrics import cagr, max_drawdown, sharpe_ratio

STANDARD_PRICE_LIMITS = {"HOSE": 0.07, "HNX": 0.10, "UPCOM": 0.15}


def _rsi(close: pd.Series, period: int) -> pd.Series:
    """Tính RSI Wilder gần đúng bằng trung bình lăn trên thay đổi tăng/giảm."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + relative_strength))


def _signals(data: pd.DataFrame, strategy: str, fast: int, slow: int, rsi_period: int) -> pd.Series:
    """Tạo vị thế mục tiêu 0/1 tại cuối mỗi phiên từ MA cross hoặc RSI."""
    close = data["close"].astype(float)
    if strategy == "ma_cross":
        fast_ma = close.rolling(fast, min_periods=fast).mean()
        slow_ma = close.rolling(slow, min_periods=slow).mean()
        state = (fast_ma > slow_ma).astype(float)
        state[slow_ma.isna()] = 0.0
        return state
    if strategy == "rsi":
        values = _rsi(close, rsi_period)
        state = pd.Series(0.0, index=data.index)
        holding = False
        for index, value in enumerate(values):
            if np.isnan(value):
                state.iloc[index] = 0.0
                continue
            if not holding and value < 30:
                holding = True
            elif holding and value > 70:
                holding = False
            state.iloc[index] = 1.0 if holding else 0.0
        return state
    raise ValueError("strategy phải là 'ma_cross' hoặc 'rsi'.")


def run_backtest(
    prices: pd.DataFrame,
    *,
    strategy: str = "ma_cross",
    fast_window: int = 20,
    slow_window: int = 50,
    rsi_period: int = 14,
    fee_bps: float = 15.0,
    slippage_bps: float = 10.0,
    initial_capital: float = 100_000_000,
    lot_size: int = 100,
    risk_free_rate: float = 0.0,
    limit_pct_by_exchange: dict[str, float] | None = None,
    benchmark_prices: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Chạy long-only backtest với phí, trượt giá, lô chẵn và mô phỏng T+2.

    `fee_bps`/`slippage_bps` là điểm cơ bản trên mỗi chiều giao dịch.
    Nếu exchange và map biên độ được đưa vào, mua ở trần hoặc bán ở sàn bị bỏ qua.
    Do chỉ khớp close ngày kế tiếp, đây là mô hình học tập, không phải mô phỏng sổ lệnh.
    """
    required = {"date", "close"}
    if not required.issubset(prices.columns):
        raise ValueError("prices cần có cột date và close.")
    if initial_capital <= 0 or lot_size <= 0 or fee_bps < 0 or slippage_bps < 0:
        raise ValueError("Vốn ban đầu/lô phải dương; phí và trượt giá không âm.")
    if strategy == "ma_cross" and (fast_window <= 0 or slow_window <= fast_window):
        raise ValueError("MA cần 0 < fast_window < slow_window.")

    data = prices.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["close"] = pd.to_numeric(data["close"], errors="coerce")
    data = data.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    if len(data) < 3:
        raise ValueError("Cần ít nhất 3 phiên giá.")
    data["target_position"] = _signals(data, strategy, fast_window, slow_window, rsi_period)

    cash = float(initial_capital)
    shares = 0
    entry_index: int | None = None
    entry_price: float | None = None
    entry_cost = 0.0
    realized_trades: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []
    total_cost_rate = (fee_bps + slippage_bps) / 10000

    for index in range(len(data)):
        row = data.iloc[index]
        close = float(row["close"])
        # Tín hiệu phiên trước được thực hiện phiên này, tránh look-ahead bias.
        desired = float(data.loc[index - 1, "target_position"]) if index > 0 else 0.0
        prev_close = float(data.loc[index - 1, "close"]) if index > 0 else close
        exchange = str(row.get("exchange", "")).upper()
        limit_pct = (limit_pct_by_exchange or {}).get(exchange)
        return_from_prev = close / prev_close - 1 if prev_close else 0.0
        at_upper_limit = limit_pct is not None and return_from_prev >= limit_pct - 1e-9
        at_lower_limit = limit_pct is not None and return_from_prev <= -limit_pct + 1e-9

        if desired > 0 and shares == 0 and not at_upper_limit:
            executable_price = close * (1 + slippage_bps / 10000)
            unit_cost = executable_price * (1 + fee_bps / 10000)
            quantity = int(cash / unit_cost / lot_size) * lot_size
            if quantity > 0:
                total = quantity * unit_cost
                cash -= total
                shares = quantity
                entry_index = index
                entry_price = executable_price
                entry_cost = total

        elif desired == 0 and shares > 0 and entry_index is not None and index >= entry_index + 2 and not at_lower_limit:
            executable_price = close * (1 - slippage_bps / 10000)
            proceeds = shares * executable_price * (1 - fee_bps / 10000)
            pnl = proceeds - entry_cost
            realized_trades.append({
                "entry_date": data.loc[entry_index, "date"],
                "exit_date": row["date"],
                "quantity": shares,
                "entry_price": entry_price,
                "exit_price": executable_price,
                "pnl": pnl,
                "return_on_cost": pnl / entry_cost if entry_cost else None,
            })
            cash += proceeds
            shares = 0
            entry_index = None
            entry_price = None
            entry_cost = 0.0

        equity = cash + shares * close
        curve.append({"date": row["date"], "equity": equity, "cash": cash, "shares": shares})

    # Định giá vị thế còn mở ở giá cuối để equity curve không bỏ sót tài sản.
    if shares > 0 and len(curve):
        last_close = float(data.iloc[-1]["close"])
        curve[-1]["equity"] = cash + shares * last_close

    curve_frame = pd.DataFrame(curve)
    equity_values = curve_frame["equity"].to_numpy(dtype=float)
    dd_amount, dd_pct = max_drawdown(equity_values)
    years = max((data["date"].iloc[-1] - data["date"].iloc[0]).days / 365.25, 0)
    cagr_value = cagr(equity_values[0], equity_values[-1], years) if years > 0 else None
    daily_returns = curve_frame["equity"].pct_change().dropna()
    sharpe = sharpe_ratio(daily_returns, risk_free_rate, 252)
    trade_pnls = [trade["pnl"] for trade in realized_trades]
    closed = [pnl for pnl in trade_pnls if pnl != 0]
    metrics = {
        "initial_capital": initial_capital,
        "final_equity": float(equity_values[-1]),
        "total_return": float(equity_values[-1] / initial_capital - 1),
        "cagr": cagr_value,
        "sharpe": sharpe,
        "max_drawdown_amount": dd_amount,
        "max_drawdown_pct": dd_pct,
        "closed_trades": len(realized_trades),
        "win_rate": sum(pnl > 0 for pnl in closed) / len(closed) if closed else None,
        "open_shares": shares,
        "buy_and_hold_return": float(data["close"].iloc[-1] / data["close"].iloc[0] - 1),
    }
    benchmark_curve = pd.DataFrame()
    if benchmark_prices is not None:
        if not {"date", "close"}.issubset(benchmark_prices.columns):
            raise ValueError("benchmark_prices cần có cột date và close.")
        benchmark = benchmark_prices[["date", "close"]].copy()
        benchmark["date"] = pd.to_datetime(benchmark["date"], errors="coerce")
        benchmark["close"] = pd.to_numeric(benchmark["close"], errors="coerce")
        benchmark = benchmark.dropna(subset=["date", "close"]).drop_duplicates("date").sort_values("date")
        comparison = curve_frame[["date", "equity"]].merge(benchmark, on="date", how="inner")
        if len(comparison) < 2 or comparison["close"].iloc[0] <= 0 or comparison["equity"].iloc[0] <= 0:
            raise ValueError("Cần ít nhất hai phiên trùng nhau để so sánh VN-Index.")
        strategy_base = float(comparison["equity"].iloc[0])
        index_base = float(comparison["close"].iloc[0])
        benchmark_curve = pd.DataFrame({
            "date": comparison["date"],
            "strategy_normalized": comparison["equity"] / strategy_base * initial_capital,
            "benchmark_normalized": comparison["close"] / index_base * initial_capital,
        })
        comparable_strategy_return = float(comparison["equity"].iloc[-1] / strategy_base - 1)
        benchmark_return = float(comparison["close"].iloc[-1] / index_base - 1)
        metrics["strategy_return_on_benchmark_window"] = comparable_strategy_return
        metrics["benchmark_return"] = benchmark_return
        metrics["benchmark_excess_return"] = comparable_strategy_return - benchmark_return
    return {
        "metrics": metrics,
        "equity_curve": curve_frame,
        "benchmark_curve": benchmark_curve,
        "trades": pd.DataFrame(realized_trades),
        "assumptions": [
            "Tín hiệu ở phiên t được khớp tại giá đóng cửa phiên t+1.",
            "T+2 được mô phỏng bằng khóa bán hai phiên sau phiên mua.",
            f"Phí mỗi chiều {fee_bps:.2f} bps; trượt giá mỗi chiều {slippage_bps:.2f} bps.",
            f"Lô giao dịch {lot_size} cổ phiếu; chỉ mua long, không dùng margin.",
            "Biên độ giá chỉ được mô phỏng nếu truyền exchange trong dữ liệu và limit_pct_by_exchange.",
            "Cổ tức, sự kiện doanh nghiệp, thuế riêng từng sàn và khớp lệnh trong phiên chưa được mô phỏng.",
        ],
    }


def fee_sensitivity(
    prices: pd.DataFrame,
    fee_levels_bps: list[float],
    **backtest_options: Any,
) -> pd.DataFrame:
    """Chạy lại cùng chiến lược ở nhiều mức phí để lượng hóa độ nhạy kết quả."""
    rows = []
    for fee_bps in fee_levels_bps:
        result = run_backtest(prices, fee_bps=float(fee_bps), **backtest_options)
        metrics = result["metrics"]
        rows.append({
            "fee_bps_each_side": float(fee_bps),
            "final_equity": metrics["final_equity"],
            "total_return": metrics["total_return"],
            "cagr": metrics["cagr"],
            "sharpe": metrics["sharpe"],
            "max_drawdown_pct": metrics["max_drawdown_pct"],
            "closed_trades": metrics["closed_trades"],
        })
    return pd.DataFrame(rows)


def portfolio_risk(
    periodic_returns: pd.Series | np.ndarray,
    portfolio_value: float,
    *,
    confidence: float = 0.95,
    simulations: int = 20_000,
    seed: int = 7,
) -> dict[str, dict[str, float]]:
    """Tính VaR/CVaR một kỳ theo lịch sử, chuẩn tắc và Monte Carlo Gaussian."""
    returns = np.asarray(periodic_returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if returns.size < 2 or portfolio_value <= 0 or not 0.5 < confidence < 1:
        raise ValueError("Cần >=2 lợi suất, giá trị danh mục dương và confidence trong (0.5, 1).")
    losses = -returns
    alpha = 1 - confidence

    def var_cvar(loss_sample: np.ndarray) -> tuple[float, float]:
        var = float(np.quantile(loss_sample, confidence))
        tail = loss_sample[loss_sample >= var]
        return var, float(tail.mean()) if tail.size else var

    hist_var, hist_cvar = var_cvar(losses)
    mean, std = float(returns.mean()), float(returns.std(ddof=1))
    param_var = -(mean + std * norm.ppf(alpha))
    param_cvar = -(mean - std * norm.pdf(norm.ppf(alpha)) / alpha)
    rng = np.random.default_rng(seed)
    simulated_losses = -(rng.normal(mean, std, size=simulations))
    mc_var, mc_cvar = var_cvar(simulated_losses)
    return {
        "historical": {"VaR": max(hist_var, 0) * portfolio_value, "CVaR": max(hist_cvar, 0) * portfolio_value},
        "parametric": {"VaR": max(param_var, 0) * portfolio_value, "CVaR": max(param_cvar, 0) * portfolio_value},
        "monte_carlo": {"VaR": max(mc_var, 0) * portfolio_value, "CVaR": max(mc_cvar, 0) * portfolio_value},
    }


def optimize_markowitz(
    returns: pd.DataFrame,
    *,
    objective: str = "max_sharpe",
    risk_free_rate: float = 0.0,
    max_weight: float = 0.4,
) -> dict[str, Any]:
    """Tối ưu danh mục long-only, tổng tỷ trọng 100%, giới hạn tỷ trọng mỗi mã."""
    clean = returns.dropna(axis=1, how="any").dropna(axis=0, how="any")
    if clean.shape[0] < 30 or clean.shape[1] < 2:
        raise ValueError("Cần ít nhất 30 kỳ lợi suất và 2 mã có dữ liệu đầy đủ.")
    count = clean.shape[1]
    if max_weight <= 0 or max_weight > 1 or count * max_weight < 1:
        raise ValueError("max_weight không khả thi với số mã hiện có.")
    mean = clean.mean().to_numpy() * 252
    covariance = clean.cov().to_numpy() * 252

    def stats(weights: np.ndarray) -> tuple[float, float, float]:
        expected_return = float(weights @ mean)
        volatility = float(np.sqrt(max(weights @ covariance @ weights, 0)))
        sharpe = (expected_return - risk_free_rate) / volatility if volatility > 0 else -np.inf
        return expected_return, volatility, sharpe

    if objective == "min_variance":
        objective_function = lambda weights: stats(weights)[1] ** 2
    elif objective == "max_sharpe":
        objective_function = lambda weights: -stats(weights)[2]
    else:
        raise ValueError("objective phải là 'min_variance' hoặc 'max_sharpe'.")
    result = minimize(
        objective_function,
        np.repeat(1 / count, count),
        method="SLSQP",
        bounds=[(0, max_weight)] * count,
        constraints=[{"type": "eq", "fun": lambda weights: np.sum(weights) - 1}],
        options={"maxiter": 1000, "ftol": 1e-10},
    )
    if not result.success:
        raise RuntimeError(f"Tối ưu danh mục không hội tụ: {result.message}")
    expected_return, volatility, sharpe = stats(result.x)
    return {
        "weights": dict(zip(clean.columns, result.x.tolist())),
        "annual_return": expected_return,
        "annual_volatility": volatility,
        "sharpe": sharpe,
        "objective": objective,
    }


def efficient_frontier(
    returns: pd.DataFrame,
    *,
    max_weight: float = 0.4,
    points: int = 25,
) -> pd.DataFrame:
    """Tạo các danh mục phương sai tối thiểu theo mức lợi suất năm mục tiêu."""
    clean = returns.dropna(axis=1, how="any").dropna(axis=0, how="any")
    if clean.shape[0] < 30 or clean.shape[1] < 2:
        raise ValueError("Cần ít nhất 30 kỳ lợi suất và 2 mã có dữ liệu đầy đủ.")
    count = clean.shape[1]
    if max_weight <= 0 or max_weight > 1 or count * max_weight < 1:
        raise ValueError("max_weight không khả thi với số mã hiện có.")
    if points < 2:
        raise ValueError("points phải từ 2 trở lên.")
    mean = clean.mean().to_numpy() * 252
    covariance = clean.cov().to_numpy() * 252
    bounds = [(0, max_weight)] * count
    sum_constraint = [{"type": "eq", "fun": lambda weights: np.sum(weights) - 1}]
    minimum_return = linprog(mean, A_eq=np.ones((1, count)), b_eq=[1], bounds=bounds, method="highs")
    maximum_return = linprog(-mean, A_eq=np.ones((1, count)), b_eq=[1], bounds=bounds, method="highs")
    if not minimum_return.success or not maximum_return.success:
        raise RuntimeError("Không xác định được miền lợi suất khả thi.")
    low, high = float(minimum_return.fun), float(-maximum_return.fun)
    targets = np.linspace(low, high, points)
    result_rows = []
    for target in targets:
        constraints = sum_constraint + [{"type": "eq", "fun": lambda weights, goal=target: float(weights @ mean - goal)}]
        result = minimize(
            lambda weights: float(weights @ covariance @ weights),
            np.repeat(1 / count, count), method="SLSQP", bounds=bounds,
            constraints=constraints, options={"maxiter": 1000, "ftol": 1e-10},
        )
        if result.success:
            variance = float(result.x @ covariance @ result.x)
            result_rows.append({
                "annual_return": float(result.x @ mean),
                "annual_volatility": float(np.sqrt(max(variance, 0))),
                **{f"weight_{symbol}": float(weight) for symbol, weight in zip(clean.columns, result.x)},
            })
    if len(result_rows) < 2:
        raise RuntimeError("Không hội tụ đủ điểm để dựng đường biên hiệu quả.")
    return pd.DataFrame(result_rows).sort_values("annual_volatility").reset_index(drop=True)
