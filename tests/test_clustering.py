import unittest

import numpy as np

from trendbot.clustering import average_linkage_labels, equal_cluster_risk_multipliers


class ClusteringTests(unittest.TestCase):
    def test_correlated_pairs_form_clusters(self):
        correlation = np.array(
            [
                [1.0, 0.95, 0.05, 0.00],
                [0.95, 1.0, 0.00, 0.05],
                [0.05, 0.00, 1.0, 0.90],
                [0.00, 0.05, 0.90, 1.0],
            ]
        )
        labels = average_linkage_labels(correlation, 2)
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[2], labels[3])
        self.assertNotEqual(labels[0], labels[2])

    def test_labels_are_deterministic(self):
        correlation = np.eye(6) * 0.8 + 0.2
        one = average_linkage_labels(correlation, 3)
        two = average_linkage_labels(correlation, 3)
        np.testing.assert_array_equal(one, two)

    def test_cluster_multipliers_equalize_full_signal_risk(self):
        correlation = np.array(
            [
                [1.0, 0.9, 0.0],
                [0.9, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        volatility = np.array([0.5, 0.5, 0.5])
        labels = np.array([0, 0, 1])
        multiplier = equal_cluster_risk_multipliers(
            correlation, volatility, labels
        )
        covariance = correlation * np.outer(volatility, volatility)
        risks = []
        for label in (0, 1):
            weights = np.zeros(3)
            indexes = labels == label
            weights[indexes] = multiplier[indexes] / volatility[indexes]
            risks.append(float(np.sqrt(weights @ covariance @ weights)))
        self.assertAlmostEqual(risks[0], risks[1], places=10)


if __name__ == "__main__":
    unittest.main()

