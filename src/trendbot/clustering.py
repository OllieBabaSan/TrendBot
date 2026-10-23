from __future__ import annotations

import heapq

import numpy as np


def average_linkage_labels(correlation: np.ndarray, n_clusters: int) -> np.ndarray:
    """Deterministic average-linkage clustering without external dependencies."""
    correlation = np.asarray(correlation, dtype=float)
    if correlation.ndim != 2 or correlation.shape[0] != correlation.shape[1]:
        raise ValueError("correlation must be square")
    n = correlation.shape[0]
    if n == 0:
        return np.zeros(0, dtype=int)
    if n_clusters < 1:
        raise ValueError("n_clusters must be positive")
    if n <= n_clusters:
        return np.arange(n, dtype=int)

    distance = np.sqrt(np.maximum(2.0 * (1.0 - correlation), 0.0))
    active = set(range(n))
    members: dict[int, list[int]] = {i: [i] for i in range(n)}
    sizes: dict[int, int] = {i: 1 for i in range(n)}
    pair_distance: dict[tuple[int, int], float] = {}
    heap: list[tuple[float, int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            value = float(distance[i, j])
            pair_distance[(i, j)] = value
            heapq.heappush(heap, (value, i, j))

    next_id = n
    while len(active) > n_clusters:
        while heap:
            value, left, right = heapq.heappop(heap)
            key = (min(left, right), max(left, right))
            if left in active and right in active and pair_distance.get(key) == value:
                break
        else:
            raise RuntimeError("clustering heap exhausted")

        active.remove(left)
        active.remove(right)
        merged = next_id
        next_id += 1
        members[merged] = members[left] + members[right]
        sizes[merged] = sizes[left] + sizes[right]
        for other in sorted(active):
            left_key = (min(left, other), max(left, other))
            right_key = (min(right, other), max(right, other))
            merged_distance = (
                sizes[left] * pair_distance[left_key]
                + sizes[right] * pair_distance[right_key]
            ) / sizes[merged]
            merged_key = (min(merged, other), max(merged, other))
            pair_distance[merged_key] = merged_distance
            heapq.heappush(heap, (merged_distance, merged_key[0], merged_key[1]))
        active.add(merged)

    labels = np.empty(n, dtype=int)
    ordered = sorted(active, key=lambda item: min(members[item]))
    for label, cluster in enumerate(ordered):
        labels[members[cluster]] = label
    return labels


def equal_cluster_risk_multipliers(
    correlation: np.ndarray,
    annual_volatility: np.ndarray,
    labels: np.ndarray,
    active: np.ndarray | None = None,
) -> np.ndarray:
    """Per-market multipliers giving clusters equal full-signal standalone risk."""
    correlation = np.asarray(correlation, dtype=float)
    volatility = np.asarray(annual_volatility, dtype=float)
    labels = np.asarray(labels, dtype=int)
    if active is None:
        active = np.ones(len(labels), dtype=bool)
    else:
        active = np.asarray(active, dtype=bool)
    covariance = correlation * np.outer(volatility, volatility)
    inverse_vol = np.where(active, 1.0 / np.maximum(volatility, 1e-12), 0.0)
    multipliers = np.ones(len(labels), dtype=float)
    for label in np.unique(labels[active]):
        indexes = np.flatnonzero((labels == label) & active)
        weights = np.zeros(len(labels), dtype=float)
        weights[indexes] = inverse_vol[indexes]
        risk = float(np.sqrt(max(weights @ covariance @ weights, 1e-12)))
        multipliers[indexes] = 1.0 / risk
    mean = float(multipliers[active].mean()) if active.any() else 1.0
    return multipliers / mean

