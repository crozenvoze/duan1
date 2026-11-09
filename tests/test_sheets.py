import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import gspread

from src.sheets import main, read_trades, upsert_prices_cache


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = values or []
        self.updates = []
        self.appended = []

    def get_all_values(self, **kwargs):
        self.read_options = kwargs
        return self.values

    def update(self, range_name, values):
        self.updates.append((range_name, values))

    def batch_update(self, data, value_input_option):
        self.updates.extend(data)

    def append_rows(self, rows, value_input_option):
        self.appended.extend(rows)


class FakeSpreadsheet:
    def __init__(self, worksheet=None):
        self.sheet = worksheet
        self.created = None

    def worksheet(self, title):
        if self.sheet is None:
            raise gspread.exceptions.WorksheetNotFound(title)
        return self.sheet

    def add_worksheet(self, title, rows, cols):
        self.sheet = FakeWorksheet()
        self.created = (title, rows, cols)
        return self.sheet


class PriceCacheTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "ticker": "FPT",
            "date": "2026-11-09",
            "open": 100000.0,
            "high": 101000.0,
            "low": 99000.0,
            "close": 100500.0,
            "volume": 123456.0,
        }

    def test_creates_cache_tab_and_appends_new_row(self):
        spreadsheet = FakeSpreadsheet()
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            added, updated = upsert_prices_cache([self.record])

        self.assertEqual(spreadsheet.created, ("Prices_Cache", 1000, 7))
        self.assertEqual((added, updated), (1, 0))
        self.assertEqual(spreadsheet.sheet.updates[0][0], "A1:G1")
        self.assertEqual(spreadsheet.sheet.appended[0][:2], ["FPT", "2026-11-09"])

    def test_updates_existing_ticker_date_without_adding_duplicate(self):
        values = [
            ["ticker", "date", "open", "high", "low", "close", "volume"],
            ["FPT", "2026-11-09", "100000.0", "101000.0", "99000.0", "100000.0", "123456.0"],
        ]
        spreadsheet = FakeSpreadsheet(FakeWorksheet(values))
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            added, updated = upsert_prices_cache([self.record])

        self.assertEqual((added, updated), (0, 1))
        self.assertEqual(spreadsheet.sheet.appended, [])
        self.assertEqual(spreadsheet.sheet.updates[0]["range"], "A2:G2")

    def test_does_not_rewrite_identical_row_returned_as_sheet_serials(self):
        # Google Sheets returns dates as serials and numeric cells as numbers
        # when UNFORMATTED_VALUE is requested.
        values = [
            ["ticker", "date", "open", "high", "low", "close", "volume"],
            ["FPT", 46335, 100000, 101000, 99000, 100500, 123456],
        ]
        spreadsheet = FakeSpreadsheet(FakeWorksheet(values))
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            added, updated = upsert_prices_cache([self.record])

        self.assertEqual((added, updated), (0, 0))
        self.assertEqual(spreadsheet.sheet.appended, [])
        self.assertEqual(spreadsheet.sheet.updates, [])
        self.assertEqual(
            spreadsheet.sheet.read_options["value_render_option"], "UNFORMATTED_VALUE"
        )
        self.assertEqual(
            spreadsheet.sheet.read_options["date_time_render_option"], "SERIAL_NUMBER"
        )

    def test_empty_update_does_not_open_sheet(self):
        with patch("src.sheets.open_spreadsheet") as open_sheet:
            self.assertEqual(upsert_prices_cache([]), (0, 0))
        open_sheet.assert_not_called()


class TradesReadTests(unittest.TestCase):
    def test_reads_raw_sheet_values_with_date_serials(self):
        worksheet = FakeWorksheet([["trade_id", "timestamp", "trade_date"]])
        spreadsheet = FakeSpreadsheet(worksheet)
        with patch("src.sheets.open_spreadsheet", return_value=spreadsheet):
            rows = read_trades()

        self.assertEqual(rows[0], ["trade_id", "timestamp", "trade_date"])
        self.assertEqual(worksheet.read_options["value_render_option"], "UNFORMATTED_VALUE")
        self.assertEqual(worksheet.read_options["date_time_render_option"], "SERIAL_NUMBER")

    def test_connection_check_does_not_print_trade_rows(self):
        output = StringIO()
        with patch("src.sheets.read_trades", return_value=[
            ["trade_id", "ticker"], ["private-id", "FPT"]
        ]), redirect_stdout(output):
            result = main()

        self.assertEqual(result, 0)
        self.assertIn("Rows read: 1", output.getvalue())
        self.assertIn("Columns: trade_id, ticker", output.getvalue())
        self.assertNotIn("private-id", output.getvalue())
        self.assertNotIn("FPT", output.getvalue())

    def test_connection_check_sanitizes_unexpected_network_errors(self):
        output = StringIO()
        with patch("src.sheets.read_trades", side_effect=OSError("sensitive error detail")), redirect_stdout(output):
            result = main()

        self.assertEqual(result, 1)
        self.assertIn("Connection failed (OSError)", output.getvalue())
        self.assertNotIn("sensitive error detail", output.getvalue())


if __name__ == "__main__":
    unittest.main()
