import unittest

import pandas as pd

from scripts.run_t1_finalist_stress_audit import scale_targets


class FinalistStressAuditTests(unittest.TestCase):
    def test_delay_moves_complete_scaled_target_without_lookahead(self):
        index = pd.date_range("2025-01-01", periods=3)
        targets = pd.DataFrame({"A": [1.0, 2.0, 3.0]}, index=index)
        multiplier = pd.DataFrame({"A": [0.5, 0.75, 1.0]}, index=index)
        delayed = scale_targets(targets, multiplier, 1)
        self.assertEqual(float(delayed.iloc[0, 0]), 0.0)
        self.assertEqual(float(delayed.iloc[1, 0]), 0.5)
        self.assertEqual(float(delayed.iloc[2, 0]), 1.5)
