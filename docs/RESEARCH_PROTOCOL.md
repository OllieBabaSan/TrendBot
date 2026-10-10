# TrendBot research protocol

## Objective

Determine whether slow, multi-horizon trend following has positive and
transferable expectancy in liquid crypto markets after realistic costs and
funding. Token selection is secondary to validating the strategy family.

## Frozen baseline

The initial baseline is specified in `TrendConfig`. Its parameters must not be
chosen by examining the final test period. Results from all markets form one
portfolio; independent token ledgers must not be added together and presented
as a realizable account.

## Evaluation sequence

1. Verify causal timing, fills, costs, funding signs, and accounting with unit
   tests and synthetic price paths.
2. Use a point-in-time liquid universe that retains delisted markets.
3. Allocate chronological design, validation, and untouched test periods.
4. Run ablations that answer structural questions rather than search hundreds
   of parameter combinations:
   - one speed versus the three-speed ensemble;
   - long-only versus long/short;
   - binary versus continuous exposure;
   - independent inverse-volatility versus portfolio risk targeting;
   - zero buffer versus buffered rebalancing;
   - concentrated liquid cohort versus broader point-in-time universe.
5. Stress costs, funding, delayed execution, missing observations, and
   correlation spikes.
6. Begin forward paper observation only after an untouched historical result
   passes predeclared gates.

## Venue portability

The user does not have Binance trading access. Binance data may provide broad
historical discovery evidence, but Binance is not the intended execution venue
or foundation of the system. A surviving strategy must be reproduced on an
accessible target venue before paper promotion, including venue-specific
listing history, symbol and contract mapping, funding, liquidity, fees,
minimum-order rules, price increments, and fill assumptions. A result that
exists only on Binance data is not sufficient.

## Initial gates

These are screening requirements, not proof of future profitability:

- positive net return in validation and untouched test periods;
- net Sharpe above 0.7 in both periods;
- no single market or month supplies more than 35% of total profit;
- remains positive at 20 basis points per turnover unit;
- drawdown and gross exposure remain within the declared limits;
- results survive at least one neighboring speed set without retuning;
- no causal-timing, accounting, or missing-data audit failures.

## Explicit exclusions

- no live execution or credentials;
- no claims based on pooled independent ledgers;
- no present-day survivor-only universe;
- no same-bar signal and fill;
- no parameter changes prompted by a handful of forward trades;
- no promotion based solely on an attractive aggregate backtest.
