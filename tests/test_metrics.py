"""Kiểm thử công thức tài chính bằng các đáp án tính tay."""

import math
import unittest

from src.metrics import (
    asset_turnover,
    cash_conversion,
    cagr,
    debt_to_equity,
    dupont_roe,
    equity_multiplier,
    expectancy,
    max_drawdown,
    net_margin,
    profit_factor,
    r_multiple,
    roa,
    roe,
    sharpe_ratio,
)


class MetricsTests(unittest.TestCase):
    """Đối chiếu các công thức với bộ số liệu nhỏ có thể tính bằng tay."""

    def test_profitability_and_dupont(self):
        self.assertAlmostEqual(net_margin(10, 100), 0.1)
        self.assertAlmostEqual(asset_turnover(100, 90, 110), 1.0)
        self.assertAlmostEqual(equity_multiplier(90, 110, 45, 55), 2.0)
        self.assertAlmostEqual(roe(10, 45, 55), 0.2)
        self.assertAlmostEqual(roa(10, 90, 110), 0.1)
        result = dupont_roe(10, 100, 90, 110, 45, 55)
        self.assertAlmostEqual(result["roe_dupont"], 0.2)

    def test_debt_cash_and_trade_statistics(self):
        self.assertAlmostEqual(debt_to_equity(40, 100), 0.4)
        self.assertAlmostEqual(cash_conversion(12, 10), 1.2)
        pnls = [1500, -750, 1125, -375]
        self.assertAlmostEqual(profit_factor(pnls), 2625 / 1125)
        self.assertAlmostEqual(expectancy(pnls), 375)
        self.assertAlmostEqual(r_multiple(1500, 105, 95, 100), 1.5)

    def test_risk_and_growth(self):
        amount, percent = max_drawdown([100, 150, 75, 120])
        self.assertAlmostEqual(amount, 75)
        self.assertAlmostEqual(percent, 0.5)
        self.assertAlmostEqual(cagr(100, 121, 2), 0.1)
        self.assertIsNone(sharpe_ratio([0.01]))
        self.assertIsNone(sharpe_ratio([0.01, 0.01]))
        self.assertTrue(math.isfinite(sharpe_ratio([0.01, -0.005, 0.02, 0.003])))

    def test_zero_denominators_return_none(self):
        self.assertIsNone(net_margin(1, 0))
        self.assertIsNone(roe(1, -1, 1))
        self.assertIsNone(debt_to_equity(1, 0))
        self.assertIsNone(cash_conversion(1, 0))
        self.assertIsNone(cagr(0, 10, 2))


if __name__ == "__main__":
    unittest.main()
