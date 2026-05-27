from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PendingState:
    """Pending tracker decisions waiting for confirmation."""

    baseline_raw: int | None = None
    baseline_pct: float | None = None
    baseline_at: float | None = None
    jump_raw: int | None = None
    jump_pct: float | None = None
    jump_at: float | None = None
    level_reset_raw: int | None = None
    level_reset_pct: float | None = None
    level_reset_previous_raw: int | None = None
    level_reset_previous_pct: float | None = None
    level_reset_at: float | None = None
    level_reset_count: int = 0

    def clear_baseline(self) -> None:
        self.baseline_raw = None
        self.baseline_pct = None
        self.baseline_at = None

    def clear_jump(self) -> None:
        self.jump_raw = None
        self.jump_pct = None
        self.jump_at = None

    def clear_level_reset(self) -> None:
        self.level_reset_raw = None
        self.level_reset_pct = None
        self.level_reset_previous_raw = None
        self.level_reset_previous_pct = None
        self.level_reset_at = None
        self.level_reset_count = 0

    def any_pending(self) -> bool:
        return any(
            value is not None
            for value in (
                self.baseline_raw,
                self.jump_raw,
                self.level_reset_raw,
            )
        )

