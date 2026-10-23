import unittest

import pandas as pd

from scripts.fetch_hyperliquid_candidate_funding import request_windows


class CandidateFundingTests(unittest.TestCase):
    def test_windows_cover_required_dates_without_spanning_more_than_twenty_days(self):
        dates = pd.DatetimeIndex(["2025-01-01", "2025-01-20", "2025-01-21", "2025-03-01"], tz="UTC")
        windows = request_windows(dates)
        self.assertEqual(len(windows), 3)
        self.assertEqual(windows[0][0], pd.Timestamp("2025-01-01", tz="UTC"))
        self.assertLess(windows[0][1] - windows[0][0], pd.Timedelta(days=20))
