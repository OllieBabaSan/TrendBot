# Public Reference Reproduction

Date: 2026-10-10

## Source and method

The unmodified portfolio engine from [Trend Atlas](https://github.com/0xpg/crypto-trend-following) commit `4aaa229f5bc9f1b762ba4f6ba5d83c9f5cfef294` was run against TrendBot's same 638-market point-in-time archive universe for 2020-2025.

Windows application control blocked a newly downloaded SciPy DLL. The reference engine itself was not edited; its three SciPy hierarchy calls were serviced by TrendBot's tested dependency-free implementation of the same average-linkage correlation-distance algorithm. The assembled daily CSVs do not retain intraday completeness counts, so every observed daily bar was represented as 24-hour complete. These substitutions are recorded in the machine-readable output.

## Architectural differences

The public default uses a 70% short plus 30% long-horizon volatility blend, signal clipping, adjusted EWM calculations, cluster-risk weighting, a 2.0x gross cap, holdings that drift before rebalancing, and gap-aware marks. TrendBot began with short volatility, no cluster weights, a 1.5x cap, and simplified weight accounting.

## Results

| Construction | Total return | Sharpe | Max drawdown | 2023 | 2024-2025 |
|---|---:|---:|---:|---:|---:|
| Corrected TrendBot baseline | +194.45% | 0.931 | -29.26% | -19.49% | +50.29% |
| Exact reference default | +136.19% | 0.838 | -32.11% | -14.91% | +63.09% |
| Reference, 1.5x cap | +135.56% | 0.836 | -32.11% | -14.91% | +62.66% |
| Reference, no clusters, 1.5x | +167.15% | **0.950** | **-21.89%** | **-12.66%** | +39.73% |
| Reference, short vol, no clusters, 1.5x | +184.81% | 0.926 | -27.77% | -17.81% | +46.76% |
| Reference, no clusters, 2.0x | +169.99% | **0.954** | **-21.64%** | **-12.38%** | +40.98% |

## Conclusions

Copying the public default is not supported. Cluster weighting materially worsened efficiency and drawdown on this broader point-in-time universe. Raising the gross cap changed little because the target rarely reached either ceiling.

The blended-volatility forecast without clusters is a credible neighbor: it improved Sharpe, drawdown, and the 2023 transition loss. It nevertheless remained negative in 2023 and surrendered substantial 2024-2025 return. It is an informative candidate for broader transition-risk testing, not a promoted replacement.

The baseline-like reference variant showed that the remaining signal and accounting details are not a hidden source of large profits. Its results were close to TrendBot's corrected baseline.

## Accounting correction

TrendBot previously treated held weights as stationary between opens, which implies small unrecorded rebalances. The engine now lets holdings drift with returns, freezes execution when an open is missing, carries gap returns to the next valid mark, and recognizes terminal settlement only after the final observable open.

After correction, the baseline changed only modestly: total return +194.45%, Sharpe 0.931, maximum drawdown -29.26%, and 2023 -19.49%. The prior economic conclusion survives, while future turnover and gap accounting are more faithful.

Machine-readable results are in `outputs/reference-reproduction.json` and `outputs/baseline-accounting-corrected.json`.
