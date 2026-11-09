"""Kiểm thử các đầu ra rủi ro và optimizer bằng dữ liệu tổng hợp."""

import unittest

import numpy as np
import pandas as pd

from src.backtest import efficient_frontier, fee_sensitivity, optimize_markowitz, portfolio_risk, run_backtest


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

    def test_vnindex_comparison_and_fee_sensitivity(self):
        dates = pd.date_range("2025-01-01", periods=20)
        prices = pd.DataFrame({"date": dates, "close": np.linspace(10, 20, len(dates))})
        benchmark = pd.DataFrame({"date": dates, "close": np.linspace(1000, 1100, len(dates))})
        result = run_backtest(prices, benchmark_prices=benchmark, fee_bps=0, slippage_bps=0)
        self.assertAlmostEqual(result["metrics"]["benchmark_return"], 0.1)
        self.assertEqual(len(result["benchmark_curve"]), len(dates))
        sensitivity = fee_sensitivity(
            prices, [0, 20], strategy="ma_cross", fast_window=2, slow_window=3,
            slippage_bps=0, initial_capital=1_000_000,
        )
        self.assertEqual(sensitivity["fee_bps_each_side"].tolist(), [0.0, 20.0])
        self.assertGreaterEqual(sensitivity.iloc[0]["final_equity"], sensitivity.iloc[1]["final_equity"])

    def test_efficient_frontier_obeys_weight_cap(self):
        rng = np.random.default_rng(18)
        returns = pd.DataFrame(rng.normal(0.0004, .01, size=(100, 3)), columns=["AAA", "BBB", "CCC"])
        frontier = efficient_frontier(returns, max_weight=.5, points=7)
        weight_columns = [column for column in frontier if column.startswith("weight_")]
        self.assertGreaterEqual(len(frontier), 2)
        for _, row in frontier.iterrows():
            self.assertAlmostEqual(sum(row[column] for column in weight_columns), 1, places=5)
            self.assertLessEqual(max(row[column] for column in weight_columns), .50001)


if __name__ == "__main__":
    unittest.main()
