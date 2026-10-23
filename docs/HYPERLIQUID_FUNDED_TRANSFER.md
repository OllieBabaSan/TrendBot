# Hyperliquid funded transfer result

Date: 2026-10-11

## Funding coverage

The candidate-only collector requested hourly funding only for market-days on
which frozen T1 could hold a nonzero target. This reduced the collection to 97
symbols and 23,344 market-days without changing signal eligibility.

Hyperliquid's early history contains three funding observations per day; 89
required days have that complete historical cadence. Later history is hourly.
Seventeen later market-days have 23 rather than 24 observations, and the first
eligible OP and SOL day lack all three early observations. This is 23 missing
intervals out of approximately 558,387 expected intervals, or about 99.996%
interval coverage. Missing observations remain zero in the central ledger and
are disclosed rather than described as exact coverage. Their maximum plausible
effect is immaterial relative to the observed strategy deterioration, but the
manifest preserves them for sensitivity checks.

Two collector failures were diagnosed and corrected during the resumable run:
a transient HTTP 500 now retries, and funding requests now preserve original
case-sensitive API names such as `kBONK` instead of using normalized CSV names.
No duplicate process or data ledger was created.

## Funded results

| Construction | Cost | Total return | Sharpe | Max drawdown | 2023 | 2024-2025 |
|---|---:|---:|---:|---:|---:|---:|
| Frozen T1 | 10 bps | +13.03% | 0.204 | -37.08% | +34.24% | -21.11% |
| 50% valve | 10 bps | +26.10% | 0.318 | -30.43% | +33.52% | -12.64% |
| 75% valve | 10 bps | +18.65% | 0.254 | -34.01% | +33.87% | -17.21% |
| Frozen T1 | 20 bps | +7.93% | 0.158 | -38.60% | +33.12% | -23.20% |
| 50% valve | 20 bps | +20.40% | 0.270 | -32.11% | +32.39% | -14.94% |
| 75% valve | 20 bps | +13.36% | 0.207 | -35.58% | +32.74% | -19.36% |

Observed funding drag is approximately 17.4-17.6 percentage points on an
arithmetic-return basis. Relative to the no-funding screen, compounded total
return falls by 21.6 points for T1, 23.9 points for the 50% valve, and 22.6
points for the 75% valve at 10 bps.

## Decision

The safety mechanism transfers: the frozen 50% valve remains clearly superior
to unchanged T1 on return, Sharpe, drawdown, and recent-period loss under both
cost assumptions. The 75% neighbor also improves T1 but is consistently weaker
than the 50% valve on this venue.

The strategy itself does not pass the promotion gate. A 0.318 funded Sharpe,
30.43% drawdown, and -12.64% result during 2024-2025 are not sufficient for a
defensible forward paper candidate, even though the aggregate return is
positive. Hyperliquid funding is not a small implementation detail; it removes
a material portion of the apparent edge.

Do not promote the zero-residual valve that scored best after this venue sample
was inspected. Do not tune funding filters or speed weights on the same period.
The next defensible work is diagnostic: attribute funding drag by market,
direction, and regime; test whether the problem is an economically coherent
long-side funding exposure that can be addressed without forecasting the
evaluation sample; and apply exact Hyperliquid order-size/minimum-notional
constraints. Forward paper remains disabled.

