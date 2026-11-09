"""Kiểm thử lọc và xếp hạng cổ phiếu bằng dữ liệu giả lập."""

import unittest

import pandas as pd

from src.screener import filter_stocks, rank_stocks


class ScreenerTests(unittest.TestCase):
    def test_filter_and_rank(self):
        data = pd.DataFrame([
            {"ticker": "AAA", "pe": 8, "pb": 1, "roe": .2, "revenue_growth": .15, "eps_growth": .12,
             "debt_to_equity": .2, "avg_value_traded": 2e9, "market_cap": 10e12, "industry": "A", "momentum": .1},
            {"ticker": "BBB", "pe": 20, "pb": 3, "roe": .1, "revenue_growth": .05, "eps_growth": .03,
             "debt_to_equity": .8, "avg_value_traded": 1e9, "market_cap": 20e12, "industry": "B", "momentum": -.1},
        ])
        filtered = filter_stocks(data, {"pe_max": 10, "industries": ["A"]})
        self.assertEqual(filtered["ticker"].tolist(), ["AAA"])
        ranked = rank_stocks(data)
        self.assertEqual(ranked.iloc[0]["ticker"], "AAA")


if __name__ == "__main__":
    unittest.main()
