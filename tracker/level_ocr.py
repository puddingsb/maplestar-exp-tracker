from __future__ import annotations

import re

from PIL import ImageOps


LEVEL_OCR_INTERVAL_TICKS = 3
LEVEL_OCR_STABLE_VOTES = 3
LEVEL_TEXT_REGEX = re.compile(r"(?:Lv\.?\s*|LV\.?\s*|Level\s*|等級\s*)?(\d{1,3})", re.IGNORECASE)


def recognize_level(image, read_texts, normalize_text, min_level, max_level, *, return_details=False):
    """Recognize a level ROI image using the caller's OCR text reader."""
    candidates = []
    seen_texts = []
    for source in (image.convert("RGB"), ImageOps.autocontrast(image.convert("L")).convert("RGB")):
        for text, confidence in read_texts(source):
            if text:
                seen_texts.append(str(text).strip())
            normalized = normalize_text(text)
            for match in LEVEL_TEXT_REGEX.finditer(normalized):
                try:
                    level = int(match.group(1))
                except ValueError:
                    continue
                if min_level <= level <= max_level:
                    candidates.append((level, confidence, str(text).strip()))
    if not candidates:
        detail = " / ".join(t for t in seen_texts if t) or "未讀到文字"
        return (None, detail) if return_details else None
    counts = {}
    confidence_by_level = {}
    text_by_level = {}
    for level, confidence, text in candidates:
        counts[level] = counts.get(level, 0) + 1
        confidence_by_level[level] = max(confidence_by_level.get(level, 0.0), confidence)
        text_by_level.setdefault(level, text)
    level = max(counts, key=lambda value: (counts[value], confidence_by_level[value]))
    if return_details:
        return level, text_by_level.get(level) or "讀到等級"
    return level
