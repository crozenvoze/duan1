"""Kiểm thử các đầu ra rủi ro và optimizer bằng dữ liệu tổng hợp."""

import unittest

import numpy as np
import pandas as pd

from src.backtest import optimize_markowitz, portfolio_risk, run_backtest


class BacktestTests(unittest.TestCase):
    def test_portfolio_risk_methods(self):
        results = portfolio_risk(np.array([-0.10, 0.0, 0.10, -0.02, 0.03]), 1_000_000, seed=1)
        self.assertEqual(set(results), {"historical", "parametric", "monte_carlo"})
        self.assertGreaterEqual(results["historical"]["CVaR"], results["historical"]["VaR"])

    def test_backtest_outputs_assumptions_and_capital(self):
        close = [10, 9, 8, 9, 10, 11, 12, 11, 10, 9, 8, 9, 10, 11, 12, 13]
        prices = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=len(close)), "close": close})
        result = run_backtest(
            prices,
            strategy="ma_cross",
            fast_window=2,
            slow_window=3,
            fee_bps=0,
            slippage_bps=0,
            initial_capital=1_000_000,
        )
        self.assertGreater(result["metrics"]["final_equity"], 0)
        self.assertTrue(any("T+2" in item for item in result["assumptions"]))

    def test_markowitz_weights_sum_to_one_and_obey_cap(self):
        rng = np.random.default_rng(4)
        base = rng.normal(0.0005, 0.01, size=(120, 1))
        values = np.hstack([base + rng.normal(0, .003, (120, 1)) for _ in range(4)])
        returns = pd.DataFrame(values, columns=["AAA", "BBB", "CCC", "DDD"])
        result = optimize_markowitz(returns, objective="min_variance", max_weight=.4)
        weights = list(result["weights"].values())
        self.assertAlmostEqual(sum(weights), 1, places=6)
        self.assertLessEqual(max(weights), .400001)
        self.assertGreaterEqual(min(weights), -1e-8)


if __name__ == "__main__":
    unittest.main()
