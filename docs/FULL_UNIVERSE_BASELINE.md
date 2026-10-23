# Point-in-time universe baseline

> Accounting update (2026-10-10): holdings now drift with market returns and
> temporary missing opens freeze execution while preserving gap P&L. The
> corrected baseline is +194.45%, Sharpe 0.931, maximum drawdown -29.26%, and
> 2023 -19.49%. See `docs\REFERENCE_REPRODUCTION.md`. Figures below preserve
> the original run for audit history.

Date: 2026-10-10

## Scope and limitations

The run uses 638 Binance USDT perpetual histories assembled from public
monthly archives from 2020 through 2025. Eligibility requires 120 prior daily
bars and trailing prior-day median quote volume of at least $5 million. Delisted
contracts remain in the data through their final observation; a held position
is marked to its final close and charged closing turnover.

This removes present-day survivor selection from market eligibility, but it is
not an epistemically untouched experiment. The architecture was selected after
reviewing public work that already reported results from part of 2024-2026.
The chronological labels below describe data flow, not prior ignorance.

## Baseline results

| Metric | Result |
|---|---:|
| Total return | +193.87% |
| CAGR | +19.67% |
| Net Sharpe | 0.920 |
| Maximum drawdown | -29.22% |
| Annual turnover | 11.23x |
| Cost drag | 6.74% of starting capital |
| Funding drag | 12.89% of starting capital |

| Period | Role | Net return |
|---|---|---:|
| 2020-2022 | design | +144.21% |
| 2023 | validation | -19.26% |
| 2024-2025 | chronological holdout | +49.05% |

Annual returns were +43.52%, +30.91%, +29.97%, -19.26%, +14.37%, and
+30.32% from 2020 through 2025 respectively. These are the corrected figures
after applying the gross-exposure ceiling to the post-buffer held book.

The baseline fails the predeclared requirement for positive validation and
test performance because 2023 is materially negative.

## Contributor dependence

- 306 markets made positive gross contributions and 192 made negative ones.
- The largest contributor supplied 6.22% of all positive gross contribution.
- The largest five supplied 22.64%.

The result is therefore not explained by a single lucky token. Its central
weakness is temporal/regime instability.

## Structural ablations

| Variant | Design 2020-22 | Validation 2023 | Holdout 2024-25 | Full Sharpe |
|---|---:|---:|---:|---:|
| Three-speed continuous long/short | +144.21% | -19.26% | +49.12% | 0.92 |
| Long-only | +28.99% | +53.52% | +0.60% | 0.66 |
| Short-only | -15.06% | -31.47% | +21.86% | -0.18 |
| Binary long/short | +114.92% | -17.93% | +38.15% | 0.78 |
| Linear long/short | +147.62% | -19.80% | +48.94% | 0.93 |
| Fast speed only | +107.36% | +1.90% | +5.51% | 0.71 |
| Medium speed only | +125.01% | -6.48% | +34.17% | 0.90 |
| Slow speed only | +105.74% | -17.79% | +2.20% | 0.53 |
| No buffer | +139.69% | -21.01% | +51.50% | 0.90 |
| Baseline at 20 bps | +138.36% | -20.59% | +45.22% | 0.87 |

## Interpretation

- Breadth changes the conclusion materially: the same architecture was weak on
  BTC/ETH/SOL but credible in aggregate across a point-in-time universe.
- Generic shorting is not independently profitable across the full period.
  It helped in 2024-2025 but was destructive in 2020-2023.
- Long-only produced the opposite profile, succeeding in 2023 but becoming
  almost flat over 2024-2025.
- Combining long and short exposure captured more total opportunity but did
  not solve the 2023 transition.
- The fast component generalized directionally across all partitions but with
  low later magnitude. Medium and slow components add return and instability.
- Continuous and linear response functions are effectively tied. Binary
  exposure increases turnover without improving robustness.
- The buffer reduces turnover and modestly improves full-period risk-adjusted
  performance. It remains justified as execution plumbing.
- Cost stress is survivable, but it does not repair the losing year.

## Disposition

Promising but not validated. Do not begin forward paper trading yet. Complete
the exposed reference architecture's cluster-risk allocation, then audit
monthly/regime losses, leverage behavior, missing funding, and sensitivity to
liquidity thresholds before deciding whether a candidate merits paper status.

