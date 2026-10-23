# External challenger tournament

Date: 2026-10-10

## Question

Before concentrating research on Candidate T1 and a transition-risk safety
valve, did the public-code search omit a stronger, reproducible crypto trading
family?

This is a bounded challenge, not a claim that every trading idea in existence
has been tested. The search covered the credible public families that can be
audited without private fills, undisclosed data, exchange access, or heroic
assumptions.

## Admission standard

A challenger needed exposed strategy logic, enough implementation detail to
reconstruct its timing, and an economically meaningful claim. It then had to
survive independent point-in-time data, lagged execution, funding, turnover
costs, chronological year attribution, and implementation review. Published
performance was not accepted as evidence by itself.

## Candidates screened

### Cross-sectional momentum and reversal

The strongest implementable challenger was
`shantanupatil14/Crypto-Cross-Sectional-Statistical-Arbitrage` at commit
`f01f132e5417ea33b5095d4e72ed0f46eb363983`.

The repository is a notebook rather than the modular package described in its
README, contains no market data, selects a fixed set of present-day survivors,
mixes Binance and Yahoo data, and repeatedly inspects its stated 2024-2025
out-of-sample interval. Its BTC exclusion also has an implementation defect:
BTC is assigned a raw zero and then cross-sectionally ranked, giving it a
nonzero target. These facts invalidate the headline as independent proof, but
the exposed alpha formula was sufficiently clear to challenge T1.

`scripts/run_momentum_reversal_challenger.py` reconstructs the final disclosed
reversal, momentum, trend, volume, and regime signal on TrendBot's 638-market
point-in-time universe. It tests both the published BTC behavior and the stated
BTC exclusion. A signal-only case isolates the alpha; a constrained case adds
the disclosed liquidity caps and deterministic dollar/beta projection in
place of the repository's optimizer. Both are tested at 10 and 20 basis points
per unit of turnover.

Best clean result, intended BTC exclusion and signal-only construction:

| Cost | Total return | Sharpe | Max drawdown | 2022 | 2023 |
|---|---:|---:|---:|---:|---:|
| 10 bps | +111.93% | 0.922 | -29.65% | -6.12% | -18.87% |
| 20 bps | +39.67% | 0.451 | -39.98% | -12.86% | -25.58% |

The published BTC bug scores +107.48%, 0.900 Sharpe, and -28.24% drawdown at
10 bps. Liquidity/beta projection does not improve the economics. Annual
turnover is about 69.5 times capital, making transaction-cost realism decisive.

Conclusion: this is real evidence of a second positive full-period alpha
family at low assumed cost, but it does not defeat T1's +194.45%, 0.931 Sharpe,
and -29.26% drawdown. It also fails the same regime-transfer objective by
losing in both 2022 and 2023 and deteriorates severely under 20-bps costs. It
is retained as a research comparator, not promoted.

### Statistical arbitrage

`abailey81/Crypto-Statistical-Arbitrage` advertises high Sharpes but provides no
market data or populated report tables. Its published result cannot be
independently reproduced as released. An independently inspectable real-data
repository, `atharvajoshi01/crypto-stat-arb`, reports negative out-of-sample
performance. This family remains theoretically valid, but no audited public
implementation cleared the evidence gate.

### Funding, basis, and market-neutral carry

These strategies are structurally different from directional trend and can be
profitable, but a valid reconstruction requires synchronized spot/perpetual or
multi-venue prices, borrow availability and cost, venue-specific funding,
margin rules, transfer latency, liquidation mechanics, and executable depth.
TrendBot currently has single-venue perpetual bars and funding observations,
not the hedge-leg data needed for a causal basis strategy. Simulating one here
would manufacture the missing execution edge. The family is therefore
separated as a future data project rather than declared failed.

### High-frequency market making and latency strategies

Public projects such as `nkaz001/hftbacktest` expose strong testing
infrastructure, not a portable profitable signal. Queue position, latency,
rebates, adverse selection, and venue-specific order-book data dominate these
systems. They are not plausible challengers on TrendBot's daily-bar dataset or
the user's present execution objective.

## Decision

The challenge does not reveal a public, independently reproducible model that
is stronger than T1 under the same evidence standard. T1 remains the incumbent
because it has the strongest net full-history result among tested candidates,
not because it is validated or guaranteed profitable. Its 2023 transition
failure remains disqualifying for deployment.

Research may now focus on a predeclared, causal disagreement/exposure safety
valve for T1 without pretending the external search proved exclusivity. The
cross-sectional challenger should remain frozen as a comparator. Any new
candidate should reopen the tournament only when it brings materially new
information, reproducible code/data, or a distinct return source—not merely a
different parameterization of an already rejected family.
