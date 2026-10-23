# 2023 Transition-Loss Audit

## Purpose

This is an attribution exercise, not a parameter-selection exercise. It asks where the baseline lost money during its known 2023 validation failure without fitting a new rule to that year.

The baseline remains the unclustered 16/48 + 32/96 + 64/192 daily trend ensemble with continuous long/short positions, inverse-volatility sizing, 20% portfolio-volatility target, 1.5x gross cap, 10% rebalance buffer, 10 bps transaction cost, funding, and point-in-time liquidity eligibility. The later accounting correction changes full-year 2023 to -19.49%; the original attribution figures below are retained as the pre-correction audit record and the machine-readable output has been refreshed.

## What failed

- Full-year 2023 net return was **-19.26%**. January (**-13.99%**) and March (**-13.07%**) were the visible transition shocks.
- Direction was highly asymmetric. Long positions contributed **+23.91% gross**, while shorts contributed **-41.34% gross**. Portfolio transaction costs were **1.66%**; funding was approximately neutral.
- January was principally an inherited-position failure. Positions already held for **91+ days lost 13.79% gross** during January. This is consistent with slow, profitable 2022 short trends surviving into an abrupt broad rebound.
- March was a different failure. Positions aged **4-10 days lost 4.55% gross** and positions aged **11-30 days lost 4.92% gross**. Both long and short exposure lost money, consistent with faster reversal/whipsaw rather than only stale inherited shorts.
- Single-speed counterfactuals confirm a speed conflict:
  - 16/48: **+1.90%** in 2023; January -7.67%, March -13.27%.
  - 32/96: **-6.48%** in 2023; January -15.41%, March -2.27%.
  - 64/192: **-17.79%** in 2023; January -13.70%, March -2.20%.
- The fixed pre-2023 eight-cluster view was not discriminating: ordinary crypto contracts collapsed into one very large correlated cluster. The losses therefore cannot be credibly assigned to a narrow industry or token group.

## Interpretation

The current ensemble averages signals before constructing one portfolio. That gives slow, established trends influence when a fast component is detecting a reversal. January shows the cost of that inertia. The opposite lesson applies to March: simply making the entire system faster is not sufficient, because the fast sleeve suffered the largest March loss.

Neither “remove shorts” nor “use only the fast signal” is supported. Long-only fixed 2023 but produced only +0.60% in the 2024-2025 chronological holdout. Fast-only fixed full-year 2023 but produced only +5.51% in 2024-2025 and remained vulnerable in March 2023. A BTC regime veto would be an after-the-fact filter and is not justified by this attribution.

## Strongest next experiment

Test **independently risk-sized speed sleeves** rather than averaging raw speed signals first. Each of 16/48, 32/96, and 64/192 would form its own causal sub-portfolio under the same eligibility, volatility, leverage, cost, and funding model; the top-level portfolio would combine the sleeves with predeclared equal risk budgets and a shared hard gross cap.

This directly addresses the observed conflict between fast reversal recognition and slow trend persistence, preserves all three economically motivated horizons, and does not require a market-regime forecast or token cherry-picking. Sleeve-level returns will also reveal whether speed diversification is real or whether one sleeve persistently subsidizes another.

Evaluate it with anchored walk-forward folds, not by optimizing on 2023 and reporting 2024-2025 again as untouched holdout. The already-viewed 2024-2025 period is corroborating evidence, not a pristine final test. Promotion requires improvement across multiple transition episodes and folds, no dependence on one year or a few contracts, tolerable turnover at 10 and 20 bps, and no leverage or delisting-control regression.

## Not recommended yet

- No live trading.
- No direction veto or BTC-200-day filter.
- No token exclusions based on 2023 losers.
- No promotion of the 12-cluster result; its sensitivity remains unresolved.
- No claim that the baseline has transferable positive expectancy. It is promising over the full history but fails a key validation year.

Machine-readable details are in `outputs/transition-loss-attribution-2023.json`.

## Speed-sleeve experiment result

The proposed equal-sleeve construction was implemented and evaluated across the full point-in-time universe. It is **not promoted**:

- Under corrected accounting, 2023 improved from **-19.49% to -7.60%**.
- Maximum full-history drawdown improved from **-29.22% to -22.91%**.
- Full-history return fell from **+194.45% to +123.14%** and Sharpe fell from **0.93 to 0.80**.
- The 2020-2022 design period fell from **+143.36% to +110.77%**.
- The already-viewed 2024-2025 corroboration period fell from **+50.29% to +14.58%**.
- Average gross exposure fell to 0.366x, but the lower Sharpe shows that simply increasing leverage would not restore the lost efficiency.

This is still informative: independent sleeves reduce transition inertia, but equal allocation over-insures the portfolio against the 2023 failure and discards too much trend payoff elsewhere. Do not optimize sleeve weights on these now-inspected years. The next defensible step is to reproduce the public reference construction more exactly and identify which simplifications in TrendBot alter its economics, then use broad walk-forward evidence for any subsequent candidate.

Machine-readable sleeve results are in `outputs/speed-sleeve-experiment.json`.
