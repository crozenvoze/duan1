import unittest
from unittest.mock import patch

import pandas as pd

from src.fundamentals import (
    FUNDAMENTALS_HEADERS,
    LEGACY_FUNDAMENTALS_HEADERS,
    calculate_fundamental_row,
    cash_conversion_quality_status,
    normalize_vnstock_statements,
    receivables_growth_status,
    write_fundamentals,
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

    def test_receivables_warning_compares_same_period_year_over_year(self):
        records = [
            {"period": "2024Q1", "revenue": 100, "receivables_ending": 40},
            {"period": "2025-Q1", "revenue": 110, "receivables_ending": 50},
        ]
        status, message = receivables_growth_status(records)
        self.assertEqual(status, "warning")
        self.assertIn("25.00%", message)
        self.assertIn("10.00%", message)
        self.assertEqual(receivables_growth_status(records[:1])[0], "unknown")

    def test_normalizer_uses_vas_ids_and_previous_period_balances(self):
        income = [
            {"period": period, "id": key, "value": value}
            for period, values in {
                "2024Q4": {"IS_NET_REVENUE": 90, "IS_GROSS_PROFIT": 30, "IS_NET_PROFIT_AFTER_TAX": 8},
                "2025Q1": {"IS_NET_REVENUE": 100, "IS_GROSS_PROFIT": 40, "IS_NET_PROFIT_AFTER_TAX": 10},
            }.items() for key, value in values.items()
        ]
        balance = [
            {"period": period, "id": key, "value": value}
            for period, values in {
                "2024Q4": {"BS_TOTAL_ASSETS": 90, "BS_OWNER_EQUITY": 45, "BS_SHORT_TERM_RECEIVABLES": 20, "BS_DEBT_SHORT": 10, "BS_DEBT_LONG": 5},
                "2025Q1": {"BS_TOTAL_ASSETS": 110, "BS_OWNER_EQUITY": 55, "BS_SHORT_TERM_RECEIVABLES": 25, "BS_DEBT_SHORT": 12, "BS_DEBT_LONG": 6},
            }.items() for key, value in values.items()
        ]
        cash_flow = [
            {"period": "2025-Q1", "id": "CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES", "value": 12}
        ]
        rows = normalize_vnstock_statements(
            "fpt",
            {"income_statement": pd.DataFrame(income), "balance_sheet": pd.DataFrame(balance), "cash_flow": pd.DataFrame(cash_flow)},
            period_type="quarter",
            borrowing_ids=("BS_DEBT_SHORT", "BS_DEBT_LONG"),
            industry="Technology",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["period"], "2025-Q1")
        self.assertEqual(rows[0]["total_borrowings"], 18)
        self.assertEqual(rows[0]["assets_beginning"], 90)
        self.assertEqual(rows[0]["equity_beginning"], 45)
        self.assertEqual(rows[0]["receivables_ending"], 25)
        self.assertEqual(rows[0]["industry"], "Technology")

    def test_normalizer_requires_explicit_borrowing_ids(self):
        with self.assertRaisesRegex(ValueError, "mã VAS khoản vay"):
            normalize_vnstock_statements("FPT", {}, period_type="quarter")

    def test_fundamentals_writer_migrates_legacy_headers_append_only(self):
        class Worksheet:
            def __init__(self):
                self.values = [LEGACY_FUNDAMENTALS_HEADERS, ["AAA", "2024Q1"] + [""] * (len(LEGACY_FUNDAMENTALS_HEADERS) - 2)]
                self.appended = []
                self.append_option = None

            def get_all_values(self):
                return self.values

            def update(self, range_name, values):
                self.values[0] = values[0]

            def append_rows(self, rows, value_input_option):
                self.appended.extend(rows)
                self.append_option = value_input_option

        class Spreadsheet:
            def __init__(self, worksheet):
                self.worksheet_value = worksheet

            def worksheet(self, title):
                return self.worksheet_value

        worksheet = Worksheet()
        record = dict(self.row, period="2025Q1", industry="Retail", receivables_ending=25)
        with patch("src.sheets.open_spreadsheet", return_value=Spreadsheet(worksheet)):
            self.assertEqual(write_fundamentals([record]), 1)

        self.assertEqual(worksheet.values[0], FUNDAMENTALS_HEADERS)
        self.assertEqual(worksheet.values[1][0:2], ["AAA", "2024Q1"])
        self.assertEqual(worksheet.appended[0][FUNDAMENTALS_HEADERS.index("industry")], "Retail")
        self.assertEqual(worksheet.appended[0][FUNDAMENTALS_HEADERS.index("receivables_ending")], 25)
        self.assertEqual(worksheet.append_option, "RAW")


if __name__ == "__main__":
    unittest.main()
