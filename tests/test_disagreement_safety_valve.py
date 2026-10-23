import unittest

import numpy as np
import pandas as pd

from scripts.run_disagreement_safety_valve import consensus_multiplier, fast_transition_multiplier, slow_inertia_multiplier


def _frame(values):
    return pd.DataFrame({"A": values, "B": values}, index=pd.date_range("2025-01-01", periods=len(values)))


class SafetyValveTests(unittest.TestCase):
    def test_consensus_rewards_unanimity_and_scales_split_vote(self):
        signs = [_frame([1, 1]), _frame([1, -1]), _frame([1, 1])]
        result = consensus_multiplier(signs, 0.25)
        self.assertTrue(np.isclose(result.iloc[0, 0], 1.0))
        self.assertTrue(np.isclose(result.iloc[1, 0], 0.50))

    def test_fast_transition_only_brakes_fast_slow_conflict(self):
        signs = [_frame([1, -1]), _frame([1, 1]), _frame([1, 1])]
        result = fast_transition_multiplier(signs, 0.5)
        self.assertTrue(np.isclose(result.iloc[0, 0], 1.0))
        self.assertTrue(np.isclose(result.iloc[1, 0], 0.5))

    def test_slow_inertia_does_not_brake_target_that_already_followed_fast(self):
        signs = [_frame([-1, -1]), _frame([1, 1]), _frame([1, 1])]
        targets = _frame([0.2, -0.2])
        result = slow_inertia_multiplier(signs, targets, 0.5)
        self.assertTrue(np.isclose(result.iloc[0, 0], 0.5))
        self.assertTrue(np.isclose(result.iloc[1, 0], 1.0))
