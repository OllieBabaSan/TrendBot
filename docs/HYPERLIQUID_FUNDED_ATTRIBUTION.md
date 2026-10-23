# Hyperliquid funded attribution audit

Date: 2026-10-12

## Scope

This is a diagnostic decomposition of the unchanged funded Hyperliquid T1,
50% fast-transition valve, and 75% valve at 10 bps. It does not tune or promote
a candidate. Headline returns compound; market-level figures below are additive
return contributions and therefore do not allocate compounding to tokens.

The repeatable audit is `scripts\run_hyperliquid_funded_attribution.py`; its
complete machine-readable result is
`outputs\hyperliquid-funded-attribution.json`. Daily net reconstruction agrees
with the simulator to within 1.4e-17.

## Main finding

The 50% valve's improvement is real, but the remaining Hyperliquid result is
not a broad, stable edge. It is a profitable long sleeve combined with a weak
short sleeve, substantial funding drag, and meaningful winner concentration.

At 10 bps, the 50% valve produced +26.10% compounded return, 0.318 Sharpe, and
-30.43% maximum drawdown. Its additive components were +52.88 percentage
points gross, -17.44 funding, and -4.63 trading costs, leaving +30.81 points
net before cross-time compounding.

## Side attribution

Across the full sample:

- Longs: +55.89 gross, -13.93 funding, -2.05 trading costs = **+39.91 net**.
- Shorts: -3.01 gross, -3.51 funding, -1.95 trading costs = **-8.48 net**.

The time split is more revealing:

- In 2023, shorts contributed **+20.58 net** and longs +9.85.
- In 2024-2025, longs remained **+11.58 net**, but shorts lost **-20.61 net**.
- In 2026 through the dataset boundary, longs contributed +18.49 and shorts
  -8.44 net.

Thus the 2024-2025 failure was not simply that funding erased all signal.
Funding consumed 11.91 points of 24.89 points of long gross performance, but
the long sleeve remained profitable. Short price timing was the larger direct
failure: shorts lost 20.21 gross points in 2024-2025 and receiving 0.57 points
of funding did not repair it.

## Funding-state attribution

Positions that paid funding generated +140.69 gross and +113.32 net. Positions
that received funding lost -86.18 gross and -80.22 net. This is association,
not causation, but it is important: a naive rule that rejects every
funding-paying trade would have removed many of the winners. Any funding-aware
control must consider expected trend payoff relative to funding magnitude,
not merely the sign of funding.

## Transition valve

For the 50% model, exposure held during fast/slow disagreement contributed
-12.75 net, while agreement exposure contributed +44.18 net. The 50% brake
therefore acts in the correct place and explains why it improves upon T1.
However, it reduces a losing state rather than converting the complete system
into a sufficiently robust one.

## Market breadth and outlier dependence

- 38 markets were positive and 59 negative.
- APE alone supplied 13.0% of all positive net contribution.
- The top five (APE, HYPE, ZEC, BTC, and MATIC) supplied 42.0% of positive net
  contribution.
- Removing only the best market leaves +20.20 additive net points.
- Removing the top five leaves **-3.44 additive net points**.

Trend following naturally relies on a minority of large winners, so this is
not automatically disqualifying. It is nevertheless material here because the
sample is venue-limited, several leaders have different listing histories,
and the risk-adjusted aggregate result is already weak.

## Decision

The audit does **not** support a simple funding-sign filter and does not support
paper promotion. It does support two narrowly defined next diagnostics:

1. Test whether the short-sleeve failure persists under causal, predeclared
   market/regime partitions and realistic execution. A long-only result may be
   reported as a diagnostic bound, but must not be selected from this inspected
   sample as a new candidate.
2. Model executable Hyperliquid sizing and slippage, then test an economically
   defined funding-burden measure (expected holding-period funding relative to
   forecast risk), rather than optimizing a funding threshold.

If the short sleeve has no stable favorable partition and the long sleeve does
not survive execution realism and outlier stress, T1 should be rejected for
Hyperliquid rather than repeatedly adjusted.
