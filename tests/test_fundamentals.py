import unittest

from src.fundamentals import (
    FUNDAMENTALS_HEADERS,
    calculate_fundamental_row,
    cash_conversion_quality_status,
)


class FundamentalsTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "ticker": "FPT",
            "period": "2025Q1",
            "revenue": 100.0,
            "gross_profit": 40.0,
            "net_income": 10.0,
            "assets_beginning": 90.0,
            "assets_ending": 110.0,
            "equity_beginning": 45.0,
            "equity_ending": 55.0,
            "total_borrowings": 20.0,
            "operating_cash_flow": 12.0,
        }

    def test_calculated_roe_is_written_to_canonical_schema(self):
        calculated = calculate_fundamental_row(self.row)
        self.assertAlmostEqual(calculated["roe"], 0.2)
        self.assertAlmostEqual(calculated["roe_direct"], 0.2)
        self.assertAlmostEqual(calculated["roe_dupont"], 0.2)
        self.assertIn("roe", FUNDAMENTALS_HEADERS)

    def test_requires_explicitly_mapped_fields(self):
        incomplete = dict(self.row)
        incomplete.pop("assets_beginning")
        with self.assertRaisesRegex(ValueError, "assets_beginning"):
            calculate_fundamental_row(incomplete)

    def test_cash_conversion_warns_only_after_two_low_positive_income_periods(self):
        level, _ = cash_conversion_quality_status([0.8, 0.7], [10, 12])
        self.assertEqual(level, "warning")
        level, _ = cash_conversion_quality_status([0.8], [10])
        self.assertEqual(level, "info")
        level, _ = cash_conversion_quality_status([0.8, 0.7], [10, -2])
        self.assertEqual(level, "unknown")


if __name__ == "__main__":
    unittest.main()
