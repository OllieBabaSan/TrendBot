import unittest

import numpy as np
import pandas as pd

from scripts.run_hyperliquid_execution_realism import (
    ExecutionAssumptions,
    round_toward_zero,
    simulate_executable_targets,
)
from trendbot.config import TrendConfig


class ExecutionRealismTests(unittest.TestCase):
    def test_lot_rounding_never_increases_absolute_order(self):
        values = np.array([1.234, -1.234, 0.009, -0.009])
        lots = np.array([0.01, 0.01, 0.01, 0.01])

        rounded = round_toward_zero(values, lots)

        np.testing.assert_allclose(rounded, [1.23, -1.23, 0.0, 0.0])
        self.assertTrue(np.all(np.abs(rounded) <= np.abs(values)))

    def test_subminimum_order_is_not_executed(self):
        index = pd.date_range("2025-01-01", periods=3, freq="D", tz="UTC")
        opens = pd.DataFrame({"X": [100.0, 110.0, 121.0]}, index=index)
        closes = opens.copy()
        targets = pd.DataFrame({"X": [0.0005, 0.0, 0.0]}, index=index)
        funding = pd.DataFrame(0.0, index=index, columns=["X"])
        volume = pd.DataFrame(10_000_000.0, index=index, columns=["X"])
        tradeable = pd.DataFrame(True, index=index, columns=["X"])
        assumptions = ExecutionAssumptions(
            initial_equity=10_000.0, taker_fee_bps=0.0,
            slippage_floor_bps=0.0, impact_coefficient=0.0
        )

        daily, positions, diagnostics = simulate_executable_targets(
            targets, opens, closes, funding, volume, tradeable,
            pd.Series({"X": 0.001}), TrendConfig(), assumptions,
        )

        self.assertTrue((positions["X"] == 0.0).all())
        self.assertEqual(diagnostics["orders_rejected_below_minimum"], 1)
        self.assertAlmostEqual(float(daily.iloc[-1]["equity"]), 10_000.0)


if __name__ == "__main__":
    unittest.main()
