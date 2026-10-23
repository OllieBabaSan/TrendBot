import unittest

import pandas as pd

from scripts.run_hyperliquid_side_diagnostics import high_liquidity_short_targets


class SideDiagnosticTests(unittest.TestCase):
    def test_liquidity_filter_uses_prior_data_and_never_removes_longs(self):
        index = pd.date_range("2025-01-01", periods=31, freq="D", tz="UTC")
        columns = ["LOW", "MID", "HIGH"]
        volume = pd.DataFrame(
            {"LOW": [1.0] * 31, "MID": [2.0] * 31, "HIGH": [3.0] * 31},
            index=index,
        )
        targets = pd.DataFrame(-0.1, index=index, columns=columns)
        targets.loc[:, "LOW"] = 0.1
        tradeable = pd.DataFrame(True, index=index, columns=columns)

        filtered = high_liquidity_short_targets(targets, volume, tradeable)

        self.assertEqual(filtered.loc[index[-1], "LOW"], 0.1)
        self.assertEqual(filtered.loc[index[-1], "MID"], 0.0)
        self.assertEqual(filtered.loc[index[-1], "HIGH"], -0.1)
        self.assertTrue((filtered.iloc[:30][["MID", "HIGH"]] == 0.0).all().all())


if __name__ == "__main__":
    unittest.main()
