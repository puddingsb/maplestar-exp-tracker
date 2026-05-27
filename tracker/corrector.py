from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class CorrectionContext:
    """Shared context for an EXP correction pipeline run."""

    visual_pct: float | None = None
    manual_level: int | None = None
    level_cap: float | None = None
    last_raw: int | None = None
    last_pct: float | None = None


@dataclass
class CorrectionResult:
    raw: int | None
    pct: float | None
    reasons: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.reasons)


CorrectionStep = Callable[[int | None, float | None, CorrectionContext], tuple[int | None, float | None, str | None] | None]


def apply_pipeline(
    raw: int | None,
    pct: float | None,
    context: CorrectionContext,
    steps: list[CorrectionStep],
) -> CorrectionResult:
    """Run correction steps once in order and collect step labels."""
    cur_raw = raw
    cur_pct = pct
    reasons: list[str] = []
    for step in steps:
        output = step(cur_raw, cur_pct, context)
        if output is None:
            continue
        next_raw, next_pct, reason = output
        if next_raw != cur_raw or next_pct != cur_pct:
            if reason:
                reasons.append(reason)
            cur_raw, cur_pct = next_raw, next_pct
    return CorrectionResult(cur_raw, cur_pct, reasons)

