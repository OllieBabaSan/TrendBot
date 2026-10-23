# Volatility-Blend Study

Date: 2026-10-10

## Question

Can a slower volatility estimate reduce the transition losses of Candidate T1 without sacrificing its transferable trend payoff?

This experiment changes only the volatility forecast used for signal normalization and inverse-volatility sizing. Trend direction, response, universe, costs, funding, portfolio target, leverage cap, and execution remain unchanged. The predeclared short-volatility weights were 0%, 25%, 50%, 70%, and 100%, with the remainder assigned to an expanding long-horizon estimate. Every point was rerun at 10 and 20 bps.

## Ten-basis-point results

| Short/long volatility | Total return | Sharpe | Max drawdown | 2023 | 2024-2025 |
|---|---:|---:|---:|---:|---:|
| Frozen 100/0 control | +194.45% | 0.931 | -29.26% | -19.49% | +50.29% |
| 0/100 | +143.45% | 0.935 | **-18.34%** | **-7.80%** | +32.89% |
| 25/75 | +150.29% | 0.939 | -19.41% | -10.52% | +36.14% |
| 50/50 | +161.48% | **0.945** | -21.68% | -12.98% | +40.14% |
| 70/30 | +172.47% | **0.944** | -24.16% | -15.12% | +43.52% |
| 100/0 with earlier availability | +192.21% | 0.925 | -28.94% | -19.15% | +49.93% |

All constructions had five positive calendar years and one negative calendar year: 2023. The progression is monotonic. Long-horizon volatility supplies drawdown protection, while short-horizon volatility supplies more upside. The middle 50/50-70/30 neighborhood has the best aggregate Sharpe, but only marginally.

## Twenty-basis-point stress

All variants remain profitable across the full history at 20 bps. The 50/50 and 70/30 neighbors retain the best Sharpe at approximately 0.889. Their 2023 returns remain negative (-14.34% and -16.46%), so added costs do not change the decision.

## Decision

No blend is promoted. The test found a robust risk-return dial, not a repaired strategy:

- long-heavy forecasts substantially soften transition drawdowns;
- short-heavy forecasts capture more of strong trends;
- neighboring middle blends modestly improve aggregate risk-adjusted results;
- every tested point still fails the declared positive-2023 validation gate;
- selecting 0/100 because it most improves 2023, or 50/50 because it has the highest measured Sharpe, would optimize an already-inspected sample.

Candidate T1 remains a useful profitable full-history benchmark, but it has not demonstrated the required regime transferability. Further tuning of its volatility blend is unlikely to manufacture the missing edge. Research should now return to the strategy-family comparison and implement Candidate T2 under the same causal universe, accounting, costs, and evaluation gates.

Machine-readable results are in `outputs/volatility-blend-study.json`.
