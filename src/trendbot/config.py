from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TrendConfig:
    speeds: tuple[tuple[int, int], ...] = ((16, 48), (32, 96), (64, 192))
    vol_window: int = 60
    vol_floor_annual: float = 0.20
    signal_scale_window: int = 365
    signal_scale_min_periods: int = 60
    annualization_days: int = 365
    target_vol_annual: float = 0.20
    max_gross_leverage: float = 1.50
    rebalance_buffer: float = 0.10
    cost_bps: float = 10.0
    initial_equity: float = 10_000.0
    response_kind: str = "tanh"
    position_mode: str = "long_short"

    def validate(self) -> None:
        if not self.speeds or any(f <= 0 or s <= f for f, s in self.speeds):
            raise ValueError("each trend speed must satisfy 0 < fast < slow")
        if self.vol_window < 2 or self.signal_scale_min_periods < 2:
            raise ValueError("rolling windows are too short")
        if self.vol_floor_annual <= 0 or self.target_vol_annual <= 0:
            raise ValueError("volatility settings must be positive")
        if self.max_gross_leverage <= 0:
            raise ValueError("gross leverage cap must be positive")
        if not 0 <= self.rebalance_buffer < 1:
            raise ValueError("rebalance buffer must be in [0, 1)")
        if self.cost_bps < 0 or self.initial_equity <= 0:
            raise ValueError("cost and equity settings are invalid")
        if self.response_kind not in {"tanh", "binary", "linear"}:
            raise ValueError("unknown response_kind")
        if self.position_mode not in {"long_short", "long_only", "short_only"}:
            raise ValueError("unknown position_mode")

    def to_dict(self) -> dict:
        return asdict(self)
