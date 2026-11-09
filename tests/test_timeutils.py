import unittest
from datetime import datetime, timezone

from src.timeutils import vietnam_today


class VietnamDateTests(unittest.TestCase):
    def test_utc_date_after_midnight_vietnam_uses_local_session_date(self):
        utc_time = datetime(2026, 11, 9, 18, 30, tzinfo=timezone.utc)
        self.assertEqual(vietnam_today(utc_time).isoformat(), "2026-11-10")

    def test_utc_time_before_midnight_vietnam_keeps_local_date(self):
        utc_time = datetime(2026, 11, 9, 16, 59, tzinfo=timezone.utc)
        self.assertEqual(vietnam_today(utc_time).isoformat(), "2026-11-09")

    def test_rejects_timezone_naive_datetime(self):
        with self.assertRaisesRegex(ValueError, "múi giờ"):
            vietnam_today(datetime(2026, 11, 10, 1, 0))


if __name__ == "__main__":
    unittest.main()
