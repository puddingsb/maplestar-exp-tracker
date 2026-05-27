from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OCRResult:
    """Structured result for one EXP OCR pass."""

    raw: int | None = None
    pct: float | None = None
    visual_pct: float | None = None
    text: str = ""
    confidence: float = 0.0
    source: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.raw is not None or self.pct is not None


@dataclass
class SampleStatus:
    """Structured state for one tracker sample decision."""

    accepted: bool = False
    state: str = ""
    reason: str = ""
    corrections: list[str] = field(default_factory=list)
    raw_after: int | None = None
    pct_after: float | None = None

