import unittest

import pandas as pd

from scripts.run_hyperliquid_funded_attribution import contribution_matrices


class FundedAttributionTests(unittest.TestCase):
    def test_components_exactly_reconstruct_daily_net(self):
        index = pd.date_range("2025-01-01", periods=3, freq="D", tz="UTC")
        opens = pd.DataFrame({"X": [100.0, 110.0, 121.0]}, index=index)
        closes = opens.copy()
        funding = pd.DataFrame({"X": [0.01, 0.01, 0.0]}, index=index)
        positions = pd.DataFrame({"X": [0.5, 0.5]}, index=index[:-1])
        first_net = 0.5 * 0.10 - 0.5 * 0.01 - 0.5 * 0.001
        drifted = 0.5 * 1.10 / (1.0 + first_net)
        second_net = 0.5 * 0.10 - 0.5 * 0.01 - abs(0.5 - drifted) * 0.001
        daily = pd.DataFrame({"net_return": [first_net, second_net]}, index=index[:-1])

        matrices = contribution_matrices(
            positions, daily, opens, closes, funding, cost_bps=10.0
        )

        pd.testing.assert_series_equal(
            matrices["net"].sum(axis=1), daily["net_return"], check_names=False
        )


if __name__ == "__main__":
    unittest.main()
