# Cluster-risk and operational diagnostics

Date: 2026-10-10

## Held-book risk correction

An audit found that the pre-buffer target respected the 1.5x gross ceiling but
the post-buffer held book could retain old positions and briefly reach 1.553x.
The hard constraint is now re-applied after buffering. A regression test covers
the case. The corrected maximum is 1.5000000000000002x (floating-point
tolerance), and the corrected control return changed only from +194.02% to
+193.87%.

## Equal cluster-risk comparison

Average-linkage correlation clustering and equal full-signal standalone risk
per cluster were implemented without external scientific dependencies.

| Variant | Total return | Sharpe | Max DD | 2023 | 2024-25 |
|---|---:|---:|---:|---:|---:|
| No cluster weights | +193.87% | 0.920 | -29.22% | -19.26% | +49.05% |
| 4 clusters | +35.84% | 0.342 | -41.10% | -27.70% | +14.56% |
| 8 clusters | +140.70% | 0.769 | -29.80% | -16.43% | +37.03% |
| 12 clusters | +207.22% | 0.925 | -30.09% | -15.24% | +80.05% |

Twelve clusters improve aggregate and later-period return but remain negative
in 2023. Four and eight clusters underperform the unclustered control. This
cluster-count sensitivity is too large to regard the 12-cluster result as a
demonstrated improvement. Cluster weighting is retained as an experimental
component, not promoted into the control.

## Liquidity sensitivity

| Prior 30-day median quote volume | Average eligible markets | Return | Sharpe | Max DD |
|---|---:|---:|---:|---:|
| $1M | 166.7 | +176.14% | 0.876 | -29.29% |
| $5M control | 141.4 | +193.87% | 0.920 | -29.22% |
| $25M | 72.7 | +164.77% | 0.868 | -23.02% |
| $100M | 29.5 | +69.33% | 0.528 | -30.51% |

The result is stable across neighboring $1M-$25M rules. Restricting the book to
only the most liquid markets materially weakens it, consistent with useful
breadth rather than an edge concentrated solely in BTC and other majors.

## Funding and exposure

- Funding archives cover 309,273 of 309,963 eligible symbol-days: 99.777%.
- Average gross exposure is 0.437x.
- Gross exposure exceeds 1x on 182 days.
- It reaches the 1.5x ceiling on four days.
- Funding drag is 12.89% of starting capital over the six-year run.

## Regime and monthly behavior

Using prior-day BTC relative to its trailing 200-day average as an observational
regime label:

- Above the average: 1,279 days, compounded portfolio return +153.37%.
- Below/unavailable: 912 days, compounded return +15.99%.

This is not a causal filter test. It shows that most expectancy is earned during
BTC-positive regimes, despite the system being long/short.

There are 42 positive and 27 negative calendar months. The two worst months are
January 2023 (-13.99%) and March 2023 (-13.07%). The 2023 loss is therefore not
uniform: it is heavily associated with transition bursts that hurt the trend
book before later stabilization.

## Disposition

The control remains promising but unvalidated. Cluster weights do not repair
the core regime transition. The next research question should target the loss
mechanism directly—directional and speed attribution around reversals—without
retrofitting a BTC regime veto to the observed failure year.

