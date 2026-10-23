# Hyperliquid venue-transfer screen

Date: 2026-10-11

## Purpose

Reproduce frozen T1 and its 50%/75% fast-transition safety valves on the venue
the user can actually access. This is a venue-transfer screen, not a paper or
live deployment.

## Data snapshot

The official Hyperliquid public info API returned 234 main-perpetual metadata
markets, including 56 marked delisted. Every market returned daily candle data.
The snapshot manifest is preserved in
`data\hyperliquid-csv\manifest.json`; raw CSV files remain local research data.

History ranges from 34 to 2,245 daily observations, averaging 988. There are
229 markets with at least 120 days, 166 with at least 557 days, and 128 with at
least 730 days. Some major candle histories predate usable venue activity, so
calendar availability alone is not accepted as tradeability.

The unchanged causal gate requires 120 prior observations and a trailing
30-day median estimated quote volume of at least $5 million. It permits its
first trade on 2023-03-23, not at the start of backfilled major-market candles.
Ninety-nine markets are eligible at least once, median simultaneous breadth is
21, maximum breadth is 45, and 33 markets qualify at the latest snapshot.

Hyperliquid candle volume is converted to estimated quote volume using candle
base volume times OHLC typical price. This is adequate for the frozen liquidity
gate but must be checked against venue notional-volume semantics before paper
promotion.

## Preliminary no-funding result

The first gate deliberately uses official Hyperliquid prices and liquidity but
zero funding. It answers whether the directional signal transfers before
incurring the much larger paginated hourly-funding collection. Results are
stored in `outputs\hyperliquid-transfer-screen-no-funding.json`.

| Construction | 10-bps return | Sharpe | Max drawdown | 2023 | 2024-2025 |
|---|---:|---:|---:|---:|---:|
| Frozen T1 | +34.64% | 0.378 | -31.74% | +43.41% | -11.46% |
| Frozen 50% valve | +50.02% | 0.497 | -24.71% | +42.53% | -2.18% |
| Frozen 75% valve | +41.24% | 0.430 | -28.50% | +42.95% | -7.19% |

At 20 bps the 50% valve remains positive overall (+43.24%) but its 2024-2025
result declines to -4.75%. The 75% valve returns +34.95% overall and -9.60% in
2024-2025. Both frozen valves improve the unchanged T1 on total return, Sharpe,
and drawdown, so the disagreement mechanism passes the initial venue-transfer
gate. Neither demonstrates stable recent-period expectancy.

The historical zero-residual-exposure brake happens to score best on this newly
inspected venue sample. It is not promoted or substituted: doing so would
reopen a parameter selected after seeing Hyperliquid. The frozen 50% and 75%
finalists remain the candidates.

## Remaining work and limitations

The official candle endpoint supplies at most 5,000 candles, which is sufficient
for the available daily history. Historical funding is hourly and paginated to
limited response sizes; exact collection across every market is materially
larger. Funding should be collected only for causally eligible/held contracts,
with an auditable completeness manifest. Until then these results are explicitly
no-funding and cannot support paper promotion.

Venue-specific fees, size increments, minimum notionals, and executable
slippage also remain to be applied. Hyperliquid metadata already records size
decimals and leverage per contract. No wallet, credentials, or order endpoint
is present in TrendBot.

## Decision

Continue the venue reproduction. The transfer result is weaker than the broad
Binance research universe, as expected from shorter history and narrower
breadth, but the frozen valves improve T1 rather than collapsing. Complete
funding and execution-cost evidence before deciding whether either candidate
deserves a forward paper lane.

