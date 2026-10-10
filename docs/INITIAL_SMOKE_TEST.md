# Initial real-data smoke test

Date: 2026-10-10

This is an engineering and directional smoke test, not strategy validation.
Its figures are superseded by the corrected fast-horizon availability and
weekly-correlation implementation plus the full-universe report in
`FULL_UNIVERSE_BASELINE.md`.
It uses only BTCUSDT, ETHUSDT, and SOLUSDT Binance perpetual daily data from
2023 through 2025. The small survivor-selected cohort is unsuitable for a
final expectancy conclusion.

## Baseline

The frozen initial three-speed, continuous long/short baseline produced:

| Period | Role | Net return |
|---|---|---:|
| 2023 | design/warm-up | +38.47% |
| 2024 | validation | +16.77% |
| 2025 | untouched test | -6.07% |

Full-period return was +51.87%, Sharpe 0.83, and maximum drawdown -22.10%.
It therefore fails the predeclared requirement for positive return in both
validation and test periods.

Funding reduced return by an arithmetic 6.33% of starting capital across the
full period. BTC and SOL were positive contributors. ETH was negative, with
its short exposure responsible for most of its gross loss.

## Structural ablations

| Variant | 2023 | 2024 | 2025 test |
|---|---:|---:|---:|
| Baseline continuous long/short | +38.47% | +16.77% | -6.07% |
| Long-only | +42.49% | +25.78% | +0.57% |
| Short-only | -6.26% | -12.39% | -0.80% |
| Binary long/short | +41.52% | +22.79% | +4.19% |
| Fast speed only | +27.64% | -7.17% | +11.05% |
| Medium speed only | +6.14% | +1.93% | -2.73% |
| Slow speed only | +52.16% | +33.40% | -14.86% |
| No rebalance buffer | +37.62% | +14.25% | -7.89% |
| Baseline at 20 bps | +37.79% | +16.08% | -6.92% |

## What this presently suggests

- The pipeline rejects the initial baseline rather than allowing positive
  aggregate performance to conceal a losing final year.
- Generic short exposure was adverse in all three years for this cohort.
- Binary exposure generalized better than continuous `tanh` exposure in this
  small sample, but this is only a research lead.
- The slow component dominated during 2023-2024 and then reversed sharply in
  2025. The ensemble reduced that single-horizon instability.
- The rebalance buffer improved every measured period while lowering turnover,
  supporting it as portfolio plumbing rather than a signal tweak.
- Doubling costs worsened results but did not explain the 2025 failure.

No baseline change is approved from this smoke test. The correct next step is
reproduction on a point-in-time liquid universe with delisted contracts, then
chronological robustness and contributor-dependence analysis.
