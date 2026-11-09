"""Các công thức tài chính chuẩn của dự án, theo định nghĩa trong Phụ lục A."""

from __future__ import annotations

from math import sqrt
from typing import Iterable

import numpy as np


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    """Chia hai số; trả None nếu thiếu dữ liệu hoặc mẫu số bằng 0."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def net_margin(net_income: float, revenue: float) -> float | None:
    """Biên lợi nhuận ròng = lợi nhuận ròng / doanh thu thuần."""
    return _divide(net_income, revenue)


def average_balance(beginning: float, ending: float) -> float:
    """Số dư bình quân = (số đầu kỳ + số cuối kỳ) / 2."""
    return (beginning + ending) / 2


def asset_turnover(revenue: float, assets_beginning: float, assets_ending: float) -> float | None:
    """Vòng quay tổng tài sản = doanh thu thuần / tổng tài sản bình quân."""
    return _divide(revenue, average_balance(assets_beginning, assets_ending))


def equity_multiplier(
    assets_beginning: float,
    assets_ending: float,
    equity_beginning: float,
    equity_ending: float,
) -> float | None:
    """Đòn bẩy vốn chủ = tổng tài sản bình quân / vốn chủ sở hữu bình quân."""
    avg_assets = average_balance(assets_beginning, assets_ending)
    avg_equity = average_balance(equity_beginning, equity_ending)
    return _divide(avg_assets, avg_equity)


def roe(net_income: float, equity_beginning: float, equity_ending: float) -> float | None:
    """ROE = lợi nhuận ròng / vốn chủ sở hữu bình quân."""
    return _divide(net_income, average_balance(equity_beginning, equity_ending))


def roa(net_income: float, assets_beginning: float, assets_ending: float) -> float | None:
    """ROA = lợi nhuận ròng / tổng tài sản bình quân."""
    return _divide(net_income, average_balance(assets_beginning, assets_ending))


def debt_to_equity(total_borrowings: float, total_equity: float) -> float | None:
    """Nợ vay/vốn chủ sở hữu; không dùng tổng nợ phải trả thay cho nợ vay."""
    return _divide(total_borrowings, total_equity)


def cash_conversion(operating_cash_flow: float, net_income: float) -> float | None:
    """Cash conversion = dòng tiền HĐKD / lợi nhuận ròng."""
    return _divide(operating_cash_flow, net_income)


def profit_factor(trade_pnls: Iterable[float]) -> float | None:
    """Profit factor = tổng lãi các sự kiện thắng / trị tuyệt đối tổng lỗ."""
    values = list(trade_pnls)
    wins = sum(value for value in values if value > 0)
    losses = abs(sum(value for value in values if value < 0))
    if losses == 0:
        return float("inf") if wins > 0 else None
    return wins / losses


def expectancy(trade_pnls: Iterable[float]) -> float | None:
    """Expectancy mỗi sự kiện = win rate × avg win − loss rate × avg loss."""
    values = list(trade_pnls)
    if not values:
        return None
    wins = [value for value in values if value > 0]
    losses = [abs(value) for value in values if value < 0]
    win_rate = len(wins) / len(values)
    loss_rate = len(losses) / len(values)
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    return win_rate * avg_win - loss_rate * avg_loss


def r_multiple(pnl: float, entry: float, stop_loss: float, quantity: int) -> float | None:
    """R-multiple = lãi/lỗ / (|giá vào − stop loss| × khối lượng)."""
    initial_risk = abs(entry - stop_loss) * quantity
    return _divide(pnl, initial_risk)


def sharpe_ratio(
    periodic_returns: Iterable[float],
    annual_risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float | None:
    """Sharpe năm hóa = (lợi suất TB − RF kỳ) / độ lệch chuẩn × căn bậc hai số kỳ.

    Đầu vào là lợi suất theo kỳ, thường là lợi suất ngày. Lãi suất phi rủi ro
    đầu vào là lãi suất năm dạng thập phân, được đổi thành RF mỗi kỳ bằng cách chia.
    """
    returns = np.asarray(list(periodic_returns), dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2 or periods_per_year <= 0:
        return None
    period_rf = annual_risk_free_rate / periods_per_year
    volatility = float(np.std(returns, ddof=1))
    if volatility == 0:
        return None
    return float((np.mean(returns) - period_rf) / volatility * sqrt(periods_per_year))


def max_drawdown(equity_values: Iterable[float]) -> tuple[float, float | None]:
    """Max drawdown trên chuỗi giá trị vốn; trả (mức tiền, tỷ lệ so với đỉnh)."""
    values = np.asarray(list(equity_values), dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return 0.0, None
    peaks = np.maximum.accumulate(values)
    drawdowns = peaks - values
    amounts = float(np.max(drawdowns))
    valid = peaks > 0
    pct = float(np.max(drawdowns[valid] / peaks[valid])) if np.any(valid) else None
    return amounts, pct


def cagr(beginning_value: float, ending_value: float, years: float) -> float | None:
    """CAGR = (giá trị cuối / giá trị đầu)^(1/số năm) − 1."""
    if beginning_value <= 0 or ending_value < 0 or years <= 0:
        return None
    return (ending_value / beginning_value) ** (1 / years) - 1


def dupont_roe(net_income: float, revenue: float, assets_beginning: float,
               assets_ending: float, equity_beginning: float, equity_ending: float) -> dict[str, float | None]:
    """Tính DuPont 3 bước: biên ròng × vòng quay tài sản × đòn bẩy vốn chủ."""
    margin = net_margin(net_income, revenue)
    turnover = asset_turnover(revenue, assets_beginning, assets_ending)
    multiplier = equity_multiplier(assets_beginning, assets_ending, equity_beginning, equity_ending)
    direct_roe = roe(net_income, equity_beginning, equity_ending)
    product = None if None in (margin, turnover, multiplier) else margin * turnover * multiplier
    return {"net_margin": margin, "asset_turnover": turnover,
            "equity_multiplier": multiplier, "roe_direct": direct_roe, "roe_dupont": product}
