import unittest

from src.fundamentals import FUNDAMENTALS_HEADERS, calculate_fundamental_row


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


if __name__ == "__main__":
    unittest.main()
