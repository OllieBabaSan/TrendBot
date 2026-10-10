# Strategy-project reset review

Date: 2026-10-10

## Original objective

Determine an effective TA trading strategy for crypto, validate that its edge
is economically meaningful and transferable, and only then build an automated
system that exercises it.

## Where BreakerBot narrowed prematurely

The literature review did not conclude that one confirmed-breakout sequence was
the best complete strategy. It found recurring evidence for several related but
distinct ideas: channel and filter rules, moving-average trend state, adaptive
no-trade bands, volatility scaling, derivatives state, cross-sectional relative
strength, and portfolios of robust rules.

The review explicitly recommended testing:

- channel breakout plus an adaptive band;
- variable-length moving-average trend plus a percentage filter;
- derivatives-state confirmation;
- the existing model as a benchmark;
- portfolios of rules that contribute independent information.

In practice, development concentrated on the channel candidate. Once its
immediate-entry form performed poorly forward, most subsequent experiments
altered the same event sequence: signal-candle range, pullback depth,
confirmation extension, stops, and rapid-failure exits. Those experiments were
useful falsification work, but they optimized the neighborhood of one thesis
instead of continuing the strategy-family comparison.

## Why that path failed the objective

1. **Family selection and parameter selection became conflated.** Evidence that
   channel rules sometimes work was treated too much like evidence for one
   channel implementation.
2. **Confirmation reused correlated price information.** Breakout, EMA state,
   pullback, confirmation close, ATR ceilings, and channel exits were largely
   transformations of the same local candles rather than independent sources
   of edge.
3. **Binary event timing dominated the design.** The system had to identify the
   right expansion candle, accept it within narrow limits, and manage it before
   a rapid failure. A trend could exist without producing that exact event.
4. **Risk engineering arrived before demonstrated expectancy.** Stops, sizing,
   simultaneous positions, and clustered exposure can shape an edge but cannot
   manufacture one.
5. **Historical token winners encouraged token-fit interpretation.** A
   right-skewed minority of winners lifted means while the median market and
   forward expanded sample remained weak.
6. **The comparison set was incomplete.** Slow continuous trend, filtered
   moving averages, pullback continuation, cross-sectional momentum, and
   ensemble timing never received comparable data, costs, and validation.
7. **The evidence budget was spent locally.** Many closely related variants
   increased multiple-testing risk without proportionately increasing what was
   learned about alternative strategy families.

## What BreakerBot taught us that remains valuable

- Same-bar indicator contamination and optimistic fills must be tested
  explicitly.
- Paper and backtest state machines must use identical timing semantics.
- Fees, slippage, funding, stop execution, and turnover can erase apparent edge.
- A positive mean can conceal a negative median and outlier dependence.
- Best-trade removal, chronological stability, neighboring parameters, and
  market/regime attribution are essential.
- Current-market universes create survivorship bias; eligibility must be
  point-in-time.
- Token ranking is secondary to strategy validation.
- Broad-market filters, tighter stops, and reduced activity do not inherently
  create profitability.
- Independent ledgers cannot be presented as a shared investable portfolio.
- Forward collection is useful only after the candidate and its falsification
  criteria are declared.

## Reset decision

TrendBot is a strategy-discovery and automation project, not merely a trend bot
despite its name. The existing slow trend implementation remains as Candidate
T1. It receives no presumption of superiority. All candidates will run through
the same data, execution clock, costs, portfolio constraints, and chronological
evaluation framework.

No candidate will be promoted because it has the highest aggregate return.
Promotion requires durable net expectancy, stability, implementability, and an
understandable source of return.

