"""
MapleStory EXP Tracker — cross-platform (Windows / macOS).
Pick the game window from a list, then drag-select the EXP region inside it.

Install:
    pip install -r requirements.txt

Run:
    python exp_tracker.py
"""

import platform
import json
import math
import os
import re
import sys
import threading
import time
import tkinter as tk
import traceback
from collections import deque
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

import mss
from PIL import Image, ImageFilter, ImageOps, ImageTk

os.environ.setdefault("DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

try:
    import numpy as np
except ImportError:
    np = None

try:
    from paddleocr import PaddleOCR
    _PP_OCR_IMPORT_ERROR = ""
except Exception as e:
    PaddleOCR = None
    _PP_OCR_IMPORT_ERROR = f"{e}\n\n{traceback.format_exc()}"

try:
    import pywinctl as pwc
except ImportError:
    pwc = None


APP_VERSION = "v2026.05.05.002"
APP_NAME = "MapleStar EXP Tracker"
APP_TITLE = f"MapleStar EXP Tracker {APP_VERSION}"
APP_AUTHOR = "作者 by 胖胖布丁小紅"
SAMPLE_INTERVAL_OPTIONS = (1, 2, 3, 5, 10)
DEFAULT_SAMPLE_INTERVAL = 1
SAMPLE_INTERVAL = float(DEFAULT_SAMPLE_INTERVAL)
HISTORY_SECONDS = 60 * 35
MAX_PREVIEW_W = 1100
MAX_PREVIEW_H = 700
REGION_PICKER_MIN_SCALE = 0.35
REGION_PICKER_MAX_SCALE = 3.0
REGION_PICKER_ZOOM_STEP = 1.25
MAX_LEVEL_CAP_RATIO_JUMP = 2.5
MIN_DELTA_TOLERANCE = 50_000
DELTA_TOLERANCE_RATIO = 4.0
CAP_TOLERANCE_RATIO = 0.0005
BACKWARD_CORRECTION_CAP_RATIO = 0.003
CONFUSED_DIGIT_CORRECTION_RATIO = 0.001
PROGRESS_RAW_TOLERANCE_RATIO = 0.025
MAX_RAW_OVER_LEVEL_CAP_RATIO = 1.02
PCT_VISUAL_MISMATCH_TOLERANCE = 2.5
MANUAL_LEVEL_AUTO_SYNC_LOOKAHEAD = 3
MANUAL_LEVEL_AUTO_SYNC_MAX_ERROR = 0.015
MAX_MANUAL_LEVEL_DRIFT = 5
MIN_LEVEL_RESET_PCT_DROP = 25.0
MIN_LEVEL_RESET_PREVIOUS_PCT = 90.0
MAX_LEVEL_RESET_CURRENT_PCT = 20.0
BASELINE_CONFIRM_CAP_RATIO = 1.20
LEVEL_ESTIMATE_MAX_ERROR = 0.08
LEVEL_SAMPLE_STRONG_MAX_ERROR = 0.025
MANUAL_LEVEL_MISMATCH_RATIO = 0.03
OCR_OVERLAP_BASE_PCT = 66.0
OCR_OVERLAP_MIN_PCT = 42.0
AUTO_LEARN_MIN_CONFIDENCE = 0.82
MAX_TEMPLATES_PER_DIGIT = 24
RATE_OUTLIER_MIN_POSITIVE_SEGMENTS = 5
RATE_OUTLIER_MULTIPLIER = 4.0
RATE_OUTLIER_MAD_MULTIPLIER = 8.0
CUMULATIVE_JUMP_CONFIRM_RATIO = 0.05
CUMULATIVE_JUMP_MIN_RATE = 3_000_000
OCR_DEBUG = True
OCR_UPSCALE_MIN_HEIGHT = 96
OCR_UPSCALE_MAX_FACTOR = 4
OCR_NEUTRALIZE_GREEN_BAR = True
EXP_REGEX = re.compile(r"([\d,]+)\D{0,8}(\d{1,3}\.\d{1,2})\s*%?")
PCT_REGEX = re.compile(r"(\d{1,3}\.\d{1,2})\s*%?")
_PP_OCR_ENGINE = None
_PP_OCR_ERROR = None
_PP_OCR_DEVICE_STATUS = "CPU"
_DIGIT_TEMPLATES = {}
_TRUSTED_DIGIT_TEMPLATES = {}
_MANUAL_DIGIT_AREA = None
_MANUAL_DIGIT_COUNT = None

# MapleStar 2026-04-02 update, "變更後" EXP required for each level.
MAPLESTAR_EXP_BY_LEVEL = {
    10: 1_350, 11: 1_534, 12: 2_090, 13: 2_730, 14: 3_549,
    15: 4_582, 16: 5_746, 17: 7_176, 18: 8_915, 19: 10_842,
    20: 13_140, 21: 15_861, 22: 18_837, 23: 22_308, 24: 26_332,
    25: 35_685, 26: 37_186, 27: 41_382, 28: 47_502, 29: 54_125,
    30: 66_990, 31: 75_936, 32: 85_932, 33: 97_066, 34: 108_878,
    35: 121_951, 36: 136_382, 37: 151_620, 38: 168_385, 39: 186_677,
    40: 205_951, 41: 226_968, 42: 249_841, 43: 273_812, 44: 299_796,
    45: 327_915, 46: 357_294, 47: 388_976, 48: 423_091, 49: 458_640,
    50: 496_801, 51: 524_025, 52: 552_741, 53: 583_031, 54: 614_981,
    55: 648_682, 56: 684_229, 57: 721_725, 58: 761_275, 59: 802_992,
    60: 846_932, 61: 893_410, 62: 942_369, 63: 994_011, 64: 1_048_482,
    65: 1_105_939, 66: 1_166_544, 67: 1_230_029, 68: 1_297_900, 69: 1_369_025,
    70: 1_547_193, 71: 1_631_979, 72: 1_721_412, 73: 1_815_744, 74: 1_915_247,
    75: 2_020_202, 76: 2_130_909, 77: 2_247_682, 78: 2_370_855, 79: 2_500_777,
    80: 2_638_427, 81: 2_782_370, 82: 2_934_845, 83: 3_095_667, 84: 3_265_317,
    85: 3_444_255, 86: 3_633_000, 87: 3_832_089, 88: 4_042_086, 89: 4_263_592,
    90: 4_497_237, 91: 4_743_685, 92: 4_963_139, 93: 5_277_838, 94: 5_567_064,
    95: 5_872_138, 96: 6_193_931, 97: 6_533_358, 98: 6_891_385, 99: 7_215_330,
    100: 7_667_376, 101: 8_087_547, 102: 8_530_745, 103: 8_998_230, 104: 9_491_681,
    105: 10_011_457, 106: 10_560_084, 107: 11_138_777, 108: 11_749_257, 109: 12_393_036,
    110: 13_072_167, 111: 13_788_529, 112: 14_544_140, 113: 15_341_158, 114: 16_181_853,
    115: 17_068_619, 116: 18_003_979, 117: 18_990_597, 118: 20_031_281, 119: 21_128_994,
    120: 23_772_654, 121: 25_075_395, 122: 26_449_526, 123: 27_898_960, 124: 29_427_822,
    125: 31_040_466, 126: 32_741_483, 127: 34_535_716, 128: 36_428_272, 129: 38_424_541,
    130: 40_530_206, 131: 42_751_261, 132: 45_094_030, 133: 47_565_183, 134: 50_171_755,
    135: 52_921_167, 136: 55_821_246, 137: 58_880_250, 138: 62_106_888, 139: 65_510_344,
    140: 69_100_311, 141: 72_887_008, 142: 76_881_216, 143: 81_094_306, 144: 85_538_273,
    145: 90_225_770, 146: 95_170_142, 147: 100_385_465, 148: 105_886_588, 149: 111_689_173,
    150: 125_172_848, 151: 132_032_320, 152: 139_267_691, 153: 146_899_636, 154: 154_949_656,
    155: 163_440_896, 156: 172_397_495, 157: 181_844_837, 158: 191_809_934, 159: 202_321_118,
    160: 213_408_315, 161: 225_103_090, 162: 245_938_739, 163: 250_450_381, 164: 264_175_062,
    165: 278_651_855, 166: 293_921_976, 167: 310_020_400, 168: 327_018_483, 169: 344_939_096,
    170: 363_841_758, 171: 383_780_287, 172: 404_811_446, 173: 426_995_113, 174: 450_394_445,
    175: 475_076_060, 176: 501_101_360, 177: 528_571_068, 178: 557_536_762, 179: 588_089_777,
    180: 656_806_337, 181: 692_799_324, 182: 730_764_727, 183: 770_810_634, 184: 813_051_056,
    185: 857_606_254, 186: 904_603_076, 187: 954_175_324, 188: 1_006_464_132, 189: 1_061_618_365,
    190: 1_119_795_051, 191: 1_181_159_820, 192: 1_245_887_378, 193: 1_322_262_006, 194: 1_386_177_633,
    195: 1_462_140_651, 196: 1_542_265_949, 197: 1_626_782_123, 198: 1_715_929_778, 199: 1_809_962_734,
}
MIN_MAPLESTAR_LEVEL = min(MAPLESTAR_EXP_BY_LEVEL)
MAX_MAPLESTAR_LEVEL = max(MAPLESTAR_EXP_BY_LEVEL)


def app_data_dir():
    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "Local"
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    return base / "MapleStar-EXP-Tracker"


OCR_DEBUG_DIR = app_data_dir() / "ocr_debug"
SETTINGS_PATH = app_data_dir() / "settings.json"
APP_ICON_PATH = ("assets", "app_icon.png")


def bundled_resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def set_app_icon(window):
    icon_path = bundled_resource_path(*APP_ICON_PATH)
    if not icon_path.exists():
        return
    try:
        photo = ImageTk.PhotoImage(Image.open(icon_path))
        window.iconphoto(True, photo)
        window._app_icon_photo = photo
    except Exception:
        pass


def normalize_ocr_text(text: str):
    table = str.maketrans(
        {
            "O": "0",
            "o": "0",
            "I": "1",
            "l": "1",
            "|": "1",
            "％": "%",
            "，": ",",
            "。": ".",
            "［": "[",
            "］": "]",
            "（": "(",
            "）": ")",
        }
    )
    return text.translate(table).replace(",", "")


def _find_percent_candidates(compact: str):
    candidates = []
    for dot in [m.start() for m in re.finditer(r"\.", compact)]:
        frac_end = dot + 1
        while frac_end < len(compact) and compact[frac_end].isdigit():
            frac_end += 1
        frac = compact[dot + 1 : frac_end]
        if len(frac) < 1:
            continue
        frac = frac[:2]

        best = None
        for start in range(max(0, dot - 3), dot):
            int_part = compact[start:dot]
            if not int_part.isdigit():
                continue
            if len(int_part) > 1 and int_part.startswith("0"):
                continue
            value = float(f"{int_part}.{frac}")
            if 0 <= value <= 100:
                candidates.append((start, frac_end, value, len(int_part)))
    return candidates


def _find_percent_candidate(compact: str, visual_pct=None):
    candidates = _find_percent_candidates(compact)
    if not candidates:
        return None

    def separator_removed(candidate):
        start, _end, pct, _int_len = candidate
        return _raw_digit_end_before_percent(compact, start, pct, visual_pct=visual_pct) < start

    def raw_len(candidate):
        start, _end, pct, _int_len = candidate
        end = _raw_digit_end_before_percent(compact, start, pct, visual_pct=visual_pct)
        return len(re.sub(r"\D+", "", compact[:end]))

    if visual_pct is not None:
        return min(
            candidates,
            key=lambda c: (
                abs(c[2] - visual_pct),
                -raw_len(c),
                c[3],
            ),
        )[:3]
    return max(
        candidates,
        key=lambda c: (
            separator_removed(c),
            c[3],
            raw_len(c),
        ),
    )[:3]


def _digits_before(compact: str, end: int):
    i = end - 1
    while i >= 0 and not compact[i].isdigit():
        i -= 1
    j = i
    while j >= 0 and compact[j].isdigit():
        j -= 1
    value = compact[j + 1 : i + 1]
    return int(value) if value else None


def _raw_digit_end_before_percent(compact: str, pct_start: int, pct: float, visual_pct=None):
    end = pct_start
    # MapleStory's bracket before the percentage is often OCR'd as "1".
    # For two-digit percentages this separator appears before the percent
    # number. For one-digit percentages, only remove it when there are two
    # adjacent "1" characters before the percent number.
    if (
        pct_start > 0
        and compact[pct_start - 1] == "1"
        and (
            pct >= 10
            or (pct_start > 1 and compact[pct_start - 2] == "1")
        )
    ):
        end = pct_start - 1
    return end


def _raw_digits_before_percent(compact: str, pct_start: int, pct: float, visual_pct=None):
    end = _raw_digit_end_before_percent(compact, pct_start, pct, visual_pct=visual_pct)
    return _digits_before(compact, end)


def parse_ocr_text(text: str, visual_pct=None):
    cleaned = normalize_ocr_text(text)
    compact = re.sub(r"\s+", "", cleaned)

    percent = _find_percent_candidate(compact, visual_pct=visual_pct)
    if percent:
        pct_start, _pct_end, pct = percent
        raw = _raw_digits_before_percent(compact, pct_start, pct, visual_pct=visual_pct)
        if raw is not None:
            return raw, pct

    m = EXP_REGEX.search(compact)
    if m:
        pct = float(m.group(2))
        if 0 <= pct <= 100:
            return int(m.group(1)), pct

    pm = PCT_REGEX.search(compact)
    pct = float(pm.group(1)) if pm else None
    if pct is not None and not 0 <= pct <= 100:
        pct = None
    return None, pct


def parse_ocr_raw(text: str, visual_pct=None):
    raw, _pct = parse_ocr_text(text, visual_pct=visual_pct)
    return raw


def raw_before_bracket(text: str):
    compact = re.sub(r"\s+", "", normalize_ocr_text(text))
    bracket_positions = [pos for pos in (compact.find("["), compact.find("(")) if pos >= 0]
    if not bracket_positions:
        return None
    bracket_at = min(bracket_positions)
    digits = "".join(ch for ch in compact[:bracket_at] if ch.isdigit())
    return int(digits) if digits else None


def exp_display(raw, pct):
    if raw is not None:
        return str(raw)
    return "—"


def exp_display_grouped(raw, pct):
    if raw is not None:
        return f"{raw:,}"
    return "—"


def level_cap_from_sample(raw, pct):
    if raw is None or pct is None or pct <= 0:
        return None
    return raw / (pct / 100)


def estimate_level_from_sample(raw, pct):
    sample_cap = level_cap_from_sample(raw, pct)
    if sample_cap is None:
        return None
    best_level, best_cap = min(
        MAPLESTAR_EXP_BY_LEVEL.items(),
        key=lambda item: abs(item[1] - sample_cap),
    )
    error = abs(best_cap - sample_cap) / max(1, best_cap)
    if error > LEVEL_ESTIMATE_MAX_ERROR:
        return None
    return best_level, best_cap, error


def level_cap_for_sample(raw, pct):
    estimate = estimate_level_from_sample(raw, pct)
    if estimate:
        return float(estimate[1])
    return level_cap_from_sample(raw, pct)


def level_display_from_estimate(estimate):
    if not estimate:
        return "—"
    level, level_cap, error = estimate
    return f"Lv {level}（{level_cap:,}）"


def is_level_reset(previous_raw, previous_pct, raw, pct):
    if previous_raw is None or previous_pct is None or raw is None or pct is None:
        return False
    if raw >= previous_raw:
        return False
    if previous_pct < MIN_LEVEL_RESET_PREVIOUS_PCT or pct > MAX_LEVEL_RESET_CURRENT_PCT:
        return False
    return previous_pct - pct >= MIN_LEVEL_RESET_PCT_DROP


def _text_component_ranges(image: Image.Image):
    rgb = image.convert("RGB")
    w, h = rgb.size
    if w < 20 or h < 8:
        return []
    y_start = max(3, int(h * 0.12))
    y_end = min(h - 3, int(h * 0.88))

    def is_text_pixel(x, y):
        r, g, b = rgb.getpixel((x, y))
        bright = max(r, g, b)
        spread = max(r, g, b) - min(r, g, b)
        greenish = g > 110 and r > 70 and b < 140 and g >= r and g - b > 25
        return bright > 145 and spread < 80 and not greenish

    allowed_rows = []
    for y in range(y_start, y_end):
        row_hits = sum(1 for x in range(w) if is_text_pixel(x, y))
        if row_hits < w * 0.35:
            allowed_rows.append(y)

    cols = []
    for x in range(w):
        ys = []
        for y in allowed_rows:
            if is_text_pixel(x, y):
                ys.append(y)
        cols.append(ys)

    ranges = []
    start = None
    for x, ys in enumerate(cols):
        if ys and start is None:
            start = x
        if ((not ys) or x == w - 1) and start is not None:
            end = x - 1 if not ys else x
            all_ys = [y for xx in range(start, end + 1) for y in cols[xx]]
            if all_ys:
                ranges.append(
                    {
                        "x0": start,
                        "x1": end,
                        "y0": min(all_ys),
                        "y1": max(all_ys),
                        "w": end - start + 1,
                        "h": max(all_ys) - min(all_ys) + 1,
                        "sum": len(all_ys),
                    }
                )
            start = None
    return ranges


def visual_raw_digit_count(image: Image.Image, pct):
    ranges = _text_component_ranges(image)
    if pct is None or len(ranges) < 6:
        return None
    pct_int_digits = len(str(int(pct)))
    if pct_int_digits < 1 or pct_int_digits > 3:
        return None

    dot_candidates = [
        i
        for i, r in enumerate(ranges)
        if r["w"] <= 3 and r["h"] <= 5 and r["sum"] <= 12
    ]
    for dot_idx in dot_candidates:
        bracket_idx = dot_idx - pct_int_digits - 1
        if bracket_idx < 1:
            continue
        bracket = ranges[bracket_idx]
        if bracket["h"] >= 8 and bracket["w"] <= 10:
            raw_components = [
                r for r in ranges[:bracket_idx] if r["w"] >= 5 and r["h"] >= 8
            ]
            return len(raw_components)
    return None


def _text_mask_array(image: Image.Image):
    rgb = image.convert("RGB")
    if np is None:
        return None
    arr = np.array(rgb)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    bright = np.maximum.reduce([r, g, b])
    spread = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    greenish = (g > 110) & (r > 70) & (b < 140) & (g >= r) & ((g - b) > 25)
    mask = (bright > 145) & (spread < 80) & (~greenish)
    h, w = mask.shape
    for y in range(h):
        if y < 3 or y > h - 4 or mask[y].sum() >= w * 0.35:
            mask[y, :] = False
    return mask


def _raw_digit_boxes(image: Image.Image, visual_pct=None):
    manual_boxes = _manual_calibrated_digit_boxes(image)
    if manual_boxes:
        return manual_boxes
    if _MANUAL_DIGIT_AREA is not None:
        return []

    ranges = _digit_component_ranges(image)
    if len(ranges) < 2:
        return []

    dot_candidates = [
        i
        for i, r in enumerate(ranges)
        if r["w"] <= 3 and r["h"] <= 5 and r["sum"] <= 12
    ]
    digit_counts = []
    if visual_pct is not None and 0 <= visual_pct <= 100:
        digit_counts.append(len(str(int(visual_pct))))
    digit_counts.extend([1, 2, 3])

    seen_counts = []
    for n in digit_counts:
        if n not in seen_counts:
            seen_counts.append(n)

    choices = []
    for dot_idx in dot_candidates:
        for pct_digits in seen_counts:
            bracket_idx = dot_idx - pct_digits - 1
            if bracket_idx < 1 or bracket_idx >= len(ranges):
                continue
            bracket = ranges[bracket_idx]
            if bracket["h"] < 8 or bracket["w"] > 6:
                continue
            raw_boxes = [
                r
                for r in ranges[:bracket_idx]
                if r["h"] >= 8 and r["w"] >= 2 and r["sum"] >= 12
            ]
            if not raw_boxes:
                continue
            expected_pct_digits = len(str(int(visual_pct))) if visual_pct is not None else pct_digits
            choices.append(
                (
                    pct_digits != expected_pct_digits,
                    abs(pct_digits - expected_pct_digits),
                    -len(raw_boxes),
                    raw_boxes,
                )
            )
    if choices:
        return sorted(choices, key=lambda item: item[:3])[0][3]

    count = visual_raw_digit_count(image, visual_pct)
    if count:
        raw_boxes = [
            r
            for r in ranges
            if r["h"] >= 8 and r["w"] >= 2 and r["sum"] >= 12
        ]
        return raw_boxes[:count]

    # At some zoom levels the bright bevel connects the whole EXP number into
    # one component. Treat the leftmost wide text component as the raw EXP
    # number and split it by the MapleStory fixed-width digit pitch.
    if ranges:
        first = ranges[0]
        split = _split_wide_digit_component(first)
        if split and len(ranges) >= 2:
            return split
    return []


def _digit_component_ranges(image: Image.Image):
    mask = _text_mask_array(image)
    if mask is None:
        return [
            r
            for r in _text_component_ranges(image)
            if r.get("x0", 0) > 20 and r.get("h", 0) >= 2
        ]

    # The MapleStory font has a bright top bevel. At some zoom levels that
    # bevel bridges adjacent characters, so component detection sees several
    # digits as one wide blob. Ignore the bevel rows for segmentation only;
    # classification still uses the full glyph box below.
    segment_mask = mask.copy()
    segment_mask[:7, :] = False
    h, w = segment_mask.shape
    cols = [np.where(segment_mask[:, x])[0] for x in range(w)]

    ranges = []
    start = None
    for x, ys in enumerate(cols):
        if x <= 20:
            continue
        if len(ys) and start is None:
            start = x
        if ((not len(ys)) or x == w - 1) and start is not None:
            end = x - 1 if not len(ys) else x
            all_ys = [y for xx in range(start, end + 1) for y in cols[xx]]
            if all_ys:
                y0 = max(0, min(all_ys) - 2)
                y1 = max(all_ys)
                item = {
                    "x0": start,
                    "x1": end,
                    "y0": y0,
                    "y1": y1,
                    "w": end - start + 1,
                    "h": y1 - y0 + 1,
                    "sum": len(all_ys),
                }
                if item["h"] >= 2 and item["sum"] >= 4:
                    ranges.append(item)
            start = None

    return ranges


def _component_boxes_for_crop(crop: Image.Image, origin_x=0, origin_y=0):
    mask = _text_mask_array(crop)
    if mask is None:
        return []

    segment_mask = mask.copy()
    segment_mask[:7, :] = False
    h, w = segment_mask.shape
    cols = [np.where(segment_mask[:, x])[0] for x in range(w)]

    ranges = []
    start = None
    for x, ys in enumerate(cols):
        if len(ys) and start is None:
            start = x
        if ((not len(ys)) or x == w - 1) and start is not None:
            end = x - 1 if not len(ys) else x
            all_ys = [y for xx in range(start, end + 1) for y in cols[xx]]
            if all_ys:
                y0 = max(0, min(all_ys) - 2)
                y1 = max(all_ys)
                item = {
                    "x0": origin_x + start,
                    "x1": origin_x + end,
                    "y0": origin_y + y0,
                    "y1": origin_y + y1,
                    "w": end - start + 1,
                    "h": y1 - y0 + 1,
                    "sum": len(all_ys),
                }
                if item["h"] >= 2 and item["sum"] >= 4:
                    ranges.append(item)
            start = None
    return ranges


def _uniform_digit_boxes_from_area(image: Image.Image, area, expected_count):
    if expected_count <= 0:
        return []
    x0, y0, x1, y1 = area
    x0 = max(0, min(image.width - 1, int(x0)))
    y0 = max(0, min(image.height - 1, int(y0)))
    x1 = max(x0, min(image.width - 1, int(x1)))
    y1 = max(y0, min(image.height - 1, int(y1)))
    crop = image.crop((x0, y0, x1 + 1, y1 + 1))

    left, right = 0, crop.width - 1
    top, bottom = 0, crop.height - 1
    mask = _text_mask_array(crop)
    if mask is not None and mask.any():
        ys, xs = np.where(mask)
        left, right = int(xs.min()), int(xs.max())
        top, bottom = int(ys.min()), int(ys.max())

    width = max(1, right - left + 1)
    height = max(1, bottom - top + 1)
    selected_width = max(1, x1 - x0 + 1)
    if width < expected_count * 6 or width < selected_width * 0.65 or height < 8:
        return []
    boxes = []
    for idx in range(expected_count):
        bx0 = left + int(round(idx * width / expected_count))
        bx1 = left + int(round((idx + 1) * width / expected_count)) - 1
        bx1 = max(bx0, bx1)
        boxes.append(
            {
                "x0": x0 + bx0,
                "x1": x0 + bx1,
                "y0": y0 + top,
                "y1": y0 + bottom,
                "w": bx1 - bx0 + 1,
                "h": bottom - top + 1,
                "sum": 0,
            }
        )
    return boxes


def _split_wide_digit_component(component):
    width = int(component.get("w", 0))
    height = int(component.get("h", 0))
    if width < 22 or height < 8:
        return []
    digit_pitch = max(7.0, height * 0.62)
    count = int(round(width / digit_pitch))
    if count < 2 or count > 12:
        return []

    x0 = int(component["x0"])
    x1 = int(component["x1"])
    y0 = int(component.get("y0", 0))
    y1 = int(component.get("y1", 0))
    boxes = []
    for idx in range(count):
        bx0 = x0 + int(round(idx * width / count))
        bx1 = x0 + int(round((idx + 1) * width / count)) - 1
        bx1 = max(bx0, min(x1, bx1))
        boxes.append(
            {
                "x0": bx0,
                "x1": bx1,
                "y0": y0,
                "y1": y1,
                "w": bx1 - bx0 + 1,
                "h": y1 - y0 + 1,
                "sum": 0,
            }
        )
    return boxes


def _manual_digit_boxes(image: Image.Image, area, expected_count):
    if expected_count <= 0:
        return []
    x0, y0, x1, y1 = area
    x0 = max(0, min(image.width - 1, int(x0)))
    y0 = max(0, min(image.height - 1, int(y0)))
    x1 = max(x0, min(image.width - 1, int(x1)))
    y1 = max(y0, min(image.height - 1, int(y1)))
    crop = image.crop((x0, y0, x1 + 1, y1 + 1))
    boxes = [
        box
        for box in _component_boxes_for_crop(crop, x0, y0)
        if box["h"] >= 8 and box["w"] >= 2 and box["sum"] >= 10
    ]
    if len(boxes) == expected_count:
        return boxes
    return _uniform_digit_boxes_from_area(image, (x0, y0, x1, y1), expected_count)


def _digit_features(mask):
    h, w = mask.shape
    if h <= 0 or w <= 0:
        return {}
    third_w = max(2, w // 3)
    quarter_h = max(2, h // 4)
    mid = h // 2

    def avg(part):
        return float(part.mean()) if part.size else 0.0

    return {
        "a": avg(mask[:quarter_h, :]),
        "g": avg(mask[max(0, mid - 1) : min(h, mid + 2), :]),
        "d": avg(mask[h - quarter_h :, :]),
        "f": avg(mask[:mid, :third_w]),
        "b": avg(mask[:mid, w - third_w :]),
        "e": avg(mask[mid:, :third_w]),
        "c": avg(mask[mid:, w - third_w :]),
    }


def _clean_digit_templates(data):
    templates = {}
    for digit, items in (data or {}).items():
        if str(digit) not in "0123456789":
            continue
        valid = [str(item) for item in items if isinstance(item, str) and len(item) == 256]
        if valid:
            templates[str(digit)] = valid[-MAX_TEMPLATES_PER_DIGIT:]
    return templates


def _set_digit_templates(data, trusted_data=None):
    global _DIGIT_TEMPLATES, _TRUSTED_DIGIT_TEMPLATES
    templates = _clean_digit_templates(data)
    trusted = _clean_digit_templates(trusted_data)
    _DIGIT_TEMPLATES = templates
    _TRUSTED_DIGIT_TEMPLATES = trusted


def _set_manual_digit_calibration(area, count):
    global _MANUAL_DIGIT_AREA, _MANUAL_DIGIT_COUNT
    try:
        parsed_area = tuple(int(v) for v in area)
        parsed_count = int(count)
    except Exception:
        _MANUAL_DIGIT_AREA = None
        _MANUAL_DIGIT_COUNT = None
        return
    if len(parsed_area) != 4 or parsed_count < 1 or parsed_count > 12:
        _MANUAL_DIGIT_AREA = None
        _MANUAL_DIGIT_COUNT = None
        return
    x0, y0, x1, y1 = parsed_area
    if x1 <= x0 or y1 <= y0:
        _MANUAL_DIGIT_AREA = None
        _MANUAL_DIGIT_COUNT = None
        return
    _MANUAL_DIGIT_AREA = parsed_area
    _MANUAL_DIGIT_COUNT = parsed_count


def _manual_calibrated_digit_boxes(image: Image.Image):
    if _MANUAL_DIGIT_AREA is None or _MANUAL_DIGIT_COUNT is None:
        return []
    x0, y0, x1, y1 = _MANUAL_DIGIT_AREA
    if x0 < 0 or y0 < 0 or x1 >= image.width or y1 >= image.height:
        return []
    return _manual_digit_boxes(image, _MANUAL_DIGIT_AREA, _MANUAL_DIGIT_COUNT)


def _digit_template_from_box(image: Image.Image, box):
    mask = _text_mask_array(image)
    if mask is None:
        return None
    x0 = max(0, int(box["x0"]))
    x1 = min(mask.shape[1] - 1, int(box["x1"]))
    y0 = max(0, int(box.get("y0", 0)))
    y1 = min(mask.shape[0] - 1, int(box.get("y1", mask.shape[0] - 1)))
    glyph = mask[y0 : y1 + 1, x0 : x1 + 1]
    if glyph.size == 0:
        return None
    img = Image.fromarray((glyph.astype("uint8") * 255), mode="L")
    img = img.resize((16, 16), Image.Resampling.NEAREST)
    arr = np.array(img) > 0
    return "".join("1" if v else "0" for v in arr.flatten())


def _classify_with_template_set(current, template_set, max_distance, min_margin=0.0):
    if not template_set:
        return None, 0.0
    cur = np.fromiter((ch == "1" for ch in current), dtype=bool)
    best_digit = None
    best_distance = 1.0
    second_distance = 1.0
    for digit, templates in template_set.items():
        digit_best = 1.0
        for template in templates:
            ref = np.fromiter((ch == "1" for ch in template), dtype=bool)
            digit_best = min(digit_best, float(np.mean(cur != ref)))
        if digit_best < best_distance:
            second_distance = best_distance
            best_distance = digit_best
            best_digit = digit
        elif digit_best < second_distance:
            second_distance = digit_best

    margin = second_distance - best_distance
    if best_digit is not None and best_distance <= max_distance and margin >= min_margin:
        return best_digit, max(0.60, 1.0 - best_distance)
    return None, 0.0


def _classify_digit_by_template(image: Image.Image, box):
    if not _DIGIT_TEMPLATES and not _TRUSTED_DIGIT_TEMPLATES:
        return None, 0.0
    current = _digit_template_from_box(image, box)
    if not current:
        return None, 0.0
    digit, confidence = _classify_with_template_set(current, _TRUSTED_DIGIT_TEMPLATES, max_distance=0.40)
    if digit is not None:
        return digit, confidence
    digit, confidence = _classify_with_template_set(current, _DIGIT_TEMPLATES, max_distance=0.22, min_margin=0.025)
    if digit is not None:
        return digit, confidence
    return None, 0.0


def _classify_digit_box(image: Image.Image, box):
    digit, confidence = _classify_digit_by_template(image, box)
    if digit is not None:
        return digit, confidence

    mask = _text_mask_array(image)
    if mask is None:
        return None, 0.0
    x0 = max(0, box["x0"])
    x1 = min(mask.shape[1] - 1, box["x1"])
    y0 = max(0, box.get("y0", 0))
    y1 = min(mask.shape[0] - 1, box.get("y1", mask.shape[0] - 1))
    glyph = mask[y0 : y1 + 1, x0 : x1 + 1]
    if glyph.size == 0:
        return None, 0.0

    if box["w"] <= 5 and box["h"] >= 8:
        return "1", 0.92

    f = _digit_features(glyph)
    a, g, d = f["a"], f["g"], f["d"]
    ul, ur, ll, lr = f["f"], f["b"], f["e"], f["c"]

    if a > 0.38 and g > 0.45 and d > 0.38 and ul > 0.45 and ur > 0.45 and ll > 0.45 and lr > 0.45:
        return "8", 0.88
    if a > 0.38 and d > 0.45 and g < 0.42 and ur > 0.34 and lr <= 0.42:
        return "2", 0.82
    if a > 0.38 and d > 0.38 and ul < 0.35 and ll < 0.25 and ur > 0.35 and lr > 0.28:
        return "3", 0.82
    if a > 0.38 and d > 0.38 and g > 0.25 and ul < 0.35 and ll < 0.35 and ur > 0.42 and lr > 0.45:
        return "3", 0.80
    if a > 0.38 and d > 0.38 and g > 0.35 and ul > 0.50 and ur < 0.35 and ll < 0.45 and lr > 0.40:
        return "5", 0.84
    if g < 0.36 and ul > 0.40 and ll > 0.35:
        return "0", 0.72
    if d < 0.28 and g > 0.45:
        return "4", 0.78
    if a > 0.38 and g > 0.48 and d > 0.38 and ur > 0.48 and lr > 0.40 and ul > 0.38 and ll <= 0.42:
        return "9", 0.82
    if a > 0.35 and g > 0.45 and d > 0.35 and ul > 0.42 and ll > 0.38 and ur < 0.50:
        return "6", 0.78
    if ul > 0.52 and ll > 0.42 and g > 0.48:
        return "6", 0.82
    if ul > 0.34 and ll < 0.24 and lr > 0.30 and g > 0.34:
        if ur > 0.30 and d > 0.35:
            return "9", 0.62
        return "5", 0.75
    if ul < 0.32 and ll < 0.30 and d < 0.32 and a > 0.34:
        return "7", 0.62
    if ul < 0.32 and ll < 0.32 and lr > 0.34 and g > 0.38 and d > 0.34:
        return "3", 0.62
    if ll > 0.30 and lr < 0.36 and g > 0.38 and d > 0.34:
        return "2", 0.60
    if a > 0.34 and d > 0.34 and g > 0.42 and ul > 0.34 and ll > 0.34:
        return "8", 0.58
    return None, 0.0


def vision_read_raw_digits(image: Image.Image, visual_pct=None):
    boxes = _raw_digit_boxes(image, visual_pct)
    if not boxes:
        return None, 0.0, ""
    digits = []
    confidences = []
    for box in boxes:
        digit, confidence = _classify_digit_box(image, box)
        if digit is None:
            return None, 0.0, ""
        digits.append(digit)
        confidences.append(confidence)
    text = "".join(digits)
    if not text:
        return None, 0.0, ""
    return int(text), sum(confidences) / len(confidences), text


def correct_raw_with_visual_split(image: Image.Image, raw, pct):
    if raw is None:
        return raw
    count = visual_raw_digit_count(image, pct)
    digits = str(raw)
    if count is None or count <= 0 or len(digits) <= count:
        return raw
    if len(digits) - count == 1 and digits[-1] != "1":
        return raw
    return int(digits[:count])


def correct_raw_by_percent_suffix(raw, ocr_pct):
    if raw is None or ocr_pct is None:
        return raw
    pct_digits = f"{ocr_pct:.2f}".replace(".", "")
    raw_digits = str(raw)
    variants = [pct_digits]
    if len(pct_digits) >= 2:
        variants.append(pct_digits[1:])
    for extra in range(1, min(len(pct_digits), len(raw_digits) - 1) + 1):
        if any(raw_digits.endswith(v[:extra]) for v in variants if len(v) >= extra):
            trimmed = raw_digits[:-extra]
            if trimmed:
                return int(trimmed)
    return raw


def sanitize_ocr_raw(raw, expected_digit_count=None):
    if raw is None:
        return None
    digits = str(raw)
    if expected_digit_count is not None and expected_digit_count >= 2:
        if len(digits) > expected_digit_count:
            digits = digits[:expected_digit_count]
            return int(digits)
        if len(digits) != expected_digit_count:
            return None
    elif len(digits) > 10:
        return None
    return raw


def expected_delta_from_percent(level_cap, pct_delta):
    if level_cap is None or pct_delta is None or pct_delta < 0:
        return None
    return level_cap * (pct_delta / 100)


def delta_tolerance(level_cap, expected_delta):
    return max(
        MIN_DELTA_TOLERANCE,
        (expected_delta or 0) * DELTA_TOLERANCE_RATIO,
        (level_cap or 0) * CAP_TOLERANCE_RATIO,
    )


def exp_text_crops(image: Image.Image):
    w, h = image.size
    crops = []
    rgb = image.convert("RGB")
    pixels = rgb.load()
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            if g > 110 and r > 80 and b < 120 and g >= r and g - b > 35:
                xs.append(x)
                ys.append(y)
    if xs and ys:
        left, right = min(xs), max(xs)
        top, bottom = min(ys), max(ys)
        if right - left > 40 and bottom - top > 8:
            y0 = max(0, top - 3)
            y1 = min(h, bottom + 4)
            bar = image.crop((left, y0, right + 1, y1))
            bw, bh = bar.size
            text_xs, text_ys = [], []
            bar_pixels = bar.convert("RGB").load()
            min_text_x = int(bw * 0.35)
            for yy in range(bh):
                if yy < 3 or yy > bh - 4:
                    continue
                for xx in range(bw):
                    if xx < min_text_x:
                        continue
                    r, g, b = bar_pixels[xx, yy]
                    bright = max(r, g, b)
                    spread = max(r, g, b) - min(r, g, b)
                    greenish = g > 110 and r > 70 and b < 130 and g >= r and g - b > 30
                    if bright > 105 and spread < 95 and not greenish:
                        text_xs.append(xx)
                        text_ys.append(yy)
            if text_xs and text_ys:
                tx0 = max(0, min(text_xs) - 4)
                tx1 = min(bw, max(text_xs) + 5)
                ty0 = max(0, min(text_ys) - 3)
                ty1 = min(bh, max(text_ys) + 4)
                if tx1 - tx0 > 12 and ty1 - ty0 > 8:
                    crops.append(bar.crop((tx0, ty0, tx1, ty1)))
            if bw >= 120:
                crops.append(bar.crop((int(bw * 0.58), 0, bw, bh)))
                crops.append(bar.crop((int(bw * 0.45), 0, bw, bh)))
                crops.append(bar.crop((int(bw * 0.35), 0, bw, bh)))
            if crops:
                return crops

    if w >= 120:
        crops.extend(
            [
                image.crop((int(w * 0.62), 0, w, h)),
                image.crop((int(w * 0.55), 0, w, h)),
                image.crop((int(w * 0.42), 0, w, h)),
            ]
        )
    crops.append(image)
    return crops


def _with_padding(image: Image.Image, padding=12, fill=(255, 255, 255)):
    if image.mode == "L":
        fill = 255
    out = Image.new(image.mode, (image.width + padding * 2, image.height + padding * 2), fill)
    out.paste(image, (padding, padding))
    return out


def neutralize_green_bar_for_ocr(image: Image.Image):
    """Darken the EXP progress fill so white digits keep a stable OCR background."""
    rgb = image.convert("RGB")
    if not OCR_NEUTRALIZE_GREEN_BAR or np is None or rgb.width < 20 or rgb.height < 8:
        return rgb

    arr = np.array(rgb)
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    bright = np.maximum.reduce([r, g, b])
    spread = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])

    strong_green = (
        (g > 120)
        & (r > 65)
        & (b < 150)
        & (g >= r)
        & ((g - b) > 35)
        & (bright > 130)
    )
    soft_green_glow = (
        (g > 105)
        & (r > 55)
        & (b < 165)
        & (g >= r)
        & ((g - b) > 24)
        & (bright > 105)
    )
    likely_text = (bright > 150) & (spread < 88) & (~strong_green)

    h, w = strong_green.shape
    row_hits = strong_green.sum(axis=1)
    green_rows = np.where(row_hits >= max(3, int(w * 0.08)))[0]
    if green_rows.size == 0:
        return rgb

    y0 = max(0, int(green_rows.min()) - 1)
    y1 = min(h, int(green_rows.max()) + 2)
    band_mask = np.zeros((h, w), dtype=bool)
    band_mask[y0:y1, :] = True

    apply_mask = band_mask & soft_green_glow & (~likely_text)
    if not apply_mask.any():
        return rgb

    out = arr.copy()
    # A fixed dark gray is more stable than grayscale conversion because the
    # green fill has highlights and stripes that otherwise survive OCR input.
    out[apply_mask] = (46, 49, 52)
    return Image.fromarray(out, "RGB")


def ocr_candidate_images(image: Image.Image):
    original = image.convert("RGB")
    processed = neutralize_green_bar_for_ocr(original)
    candidates = [("原始截圖", original)]
    if processed.tobytes() != original.tobytes():
        candidates.append(("去綠條OCR圖", processed))
    for idx, crop in enumerate(exp_text_crops(image)[:4], start=1):
        candidates.append((f"文字裁切_{idx}", crop.convert("RGB")))

    unique = []
    seen = set()
    for label, candidate in candidates:
        key = (candidate.size, candidate.tobytes())
        if key in seen:
            continue
        seen.add(key)
        unique.append((label, candidate))
    return unique


def ocr_device_status():
    return _PP_OCR_DEVICE_STATUS


def _ocr_cpu_threads():
    count = os.cpu_count() or 4
    return max(2, min(8, count))


PP_OCR_MODELS = (
    "PP-OCRv5_mobile_det",
    "en_PP-OCRv5_mobile_rec",
)


def _paddlex_model_dir(model_name):
    bundled = bundled_resource_path("paddlex_models", model_name)
    if bundled.exists():
        return str(bundled)
    cached = Path.home() / ".paddlex" / "official_models" / model_name
    if cached.exists():
        return str(cached)
    return None


def _pp_ocr_engine():
    global _PP_OCR_ENGINE, _PP_OCR_ERROR, _PP_OCR_DEVICE_STATUS
    if _PP_OCR_ENGINE is not None:
        return _PP_OCR_ENGINE
    if PaddleOCR is None or np is None:
        _PP_OCR_ERROR = _PP_OCR_IMPORT_ERROR or "PP-OCRv5 未安裝"
        _PP_OCR_DEVICE_STATUS = "不可用"
        return None

    try:
        kwargs = {
            "device": "cpu",
            "engine": "paddle_static",
            "enable_mkldnn": False,
            "cpu_threads": _ocr_cpu_threads(),
            "text_detection_model_name": "PP-OCRv5_mobile_det",
            "text_recognition_model_name": "en_PP-OCRv5_mobile_rec",
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "text_rec_score_thresh": 0.0,
            "text_det_thresh": 0.1,
            "text_det_box_thresh": 0.1,
            "text_det_unclip_ratio": 1.5,
            "text_det_limit_side_len": 1920,
            "text_det_limit_type": "max",
        }
        model_dir_keys = {
            "text_detection_model_dir": "PP-OCRv5_mobile_det",
            "text_recognition_model_dir": "en_PP-OCRv5_mobile_rec",
        }
        for key, model_name in model_dir_keys.items():
            model_dir = _paddlex_model_dir(model_name)
            if model_dir:
                kwargs[key] = model_dir
        _PP_OCR_DEVICE_STATUS = f"CPU（PP-OCRv5 / PaddleOCR，{_ocr_cpu_threads()} 執行緒）"
        _PP_OCR_ENGINE = PaddleOCR(**kwargs)
        _PP_OCR_ERROR = None
        return _PP_OCR_ENGINE
    except Exception as e:
        _PP_OCR_ERROR = f"{e}\n\n{traceback.format_exc()}"
        _PP_OCR_DEVICE_STATUS = "初始化失敗"
        return None


def _ocr_input_image(image: Image.Image):
    prepared = neutralize_green_bar_for_ocr(image)
    if prepared.height <= 0:
        return prepared
    if prepared.height >= OCR_UPSCALE_MIN_HEIGHT:
        return prepared
    scale = min(OCR_UPSCALE_MAX_FACTOR, max(1, math.ceil(OCR_UPSCALE_MIN_HEIGHT / prepared.height)))
    if scale <= 1:
        return prepared
    return prepared.resize(
        (prepared.width * scale, prepared.height * scale),
        Image.Resampling.LANCZOS,
    )


def ocr_texts(image: Image.Image):
    engine = _pp_ocr_engine()
    if engine is None:
        return []
    prepared = _ocr_input_image(image)
    out = []
    try:
        result = engine.predict(np.array(prepared))
    except Exception as e:
        global _PP_OCR_ERROR
        _PP_OCR_ERROR = str(e)
        return []

    normalized_items = []
    for page in list(result or []):
        try:
            data = dict(page)
        except Exception:
            continue
        ocr_res = data.get("overall_ocr_res") or data
        texts = list(ocr_res.get("rec_texts") or [])
        scores = list(ocr_res.get("rec_scores") or [])
        if len(texts) > 1:
            joined = "".join(str(text).strip() for text in texts if str(text).strip())
            if joined:
                confidence = sum(float(score) for score in scores) / len(scores) if scores else 0.0
                normalized_items.append((joined, confidence))
        for idx, text in enumerate(texts):
            text = str(text).strip()
            if not text:
                continue
            try:
                confidence = float(scores[idx]) if idx < len(scores) else 0.0
            except Exception:
                confidence = 0.0
            normalized_items.append((text, confidence))

    seen_texts = set()
    for text, confidence in normalized_items:
        if text in seen_texts:
            continue
        seen_texts.add(text)
        out.append((text, confidence))
    return out


def ocr_variants(image: Image.Image):
    rgb = image.convert("RGB")
    gray = rgb.convert("L")
    gray = ImageOps.autocontrast(gray)
    variants = []

    tight_white = Image.new("L", rgb.size, 255)
    loose_white = Image.new("L", rgb.size, 255)
    src = rgb.load()
    tight_dst = tight_white.load()
    loose_dst = loose_white.load()
    for y in range(rgb.height):
        for x in range(rgb.width):
            r, g, b = src[x, y]
            bright = max(r, g, b)
            spread = max(r, g, b) - min(r, g, b)
            greenish = g > 110 and r > 70 and b < 130 and g >= r and g - b > 30
            if bright > 145 and spread < 80 and not greenish:
                tight_dst[x, y] = 0
            if bright > 95 and spread < 105 and not greenish:
                loose_dst[x, y] = 0
    variants.append(tight_white)
    variants.append(loose_white)
    variants.append(loose_white.filter(ImageFilter.MinFilter(3)))
    variants.append(gray)
    return variants


def estimate_bar_percent(image: Image.Image):
    rgb = image.convert("RGB")
    w, h = rgb.size
    if w < 80 or h < 8:
        return None
    pixels = rgb.load()
    col_hits = []
    for x in range(w):
        hits = 0
        for y in range(max(0, int(h * 0.18)), min(h, int(h * 0.82))):
            r, g, b = pixels[x, y]
            if g > 135 and r > 95 and b < 115 and g >= r and g - b > 40:
                hits += 1
        col_hits.append(hits)

    threshold = max(2, int(h * 0.18))
    green_cols = [i for i, hits in enumerate(col_hits) if hits >= threshold]
    if len(green_cols) < 2:
        return None

    left = min(green_cols)
    right = w - 1
    # The selected area often ends at the percentage text, not at the true bar
    # edge. Prefer the right edge of the gray/green bar if we can see it.
    bar_cols = []
    for x in range(left, w):
        hits = 0
        for y in range(max(0, int(h * 0.18)), min(h, int(h * 0.82))):
            r, g, b = pixels[x, y]
            gray_bar = 45 <= r <= 150 and 45 <= g <= 150 and 45 <= b <= 150 and abs(r - g) < 35 and abs(g - b) < 35
            green_bar = g > 100 and r > 70 and b < 140 and g >= r and g - b > 25
            if gray_bar or green_bar:
                hits += 1
        if hits >= threshold:
            bar_cols.append(x)
    if bar_cols:
        right = max(bar_cols)
    width = right - left + 1
    if width < 80:
        return None

    # Search from the right edge of the bar for the last clearly filled column.
    filled = [i for i in range(left, right + 1) if col_hits[i] >= threshold]
    if not filled:
        return None
    filled_right = max(filled)
    pct = (filled_right - left + 1) / width * 100
    if 0 <= pct <= 100:
        return pct
    return None


def _ocr_score(raw, pct, text, confidence=0.0, visual_pct=None):
    score = confidence * 100
    if pct is not None:
        score += 200
        if visual_pct is not None:
            score += max(0, 120 - abs(pct - visual_pct) * 30)
    if raw is not None:
        score += min(len(str(raw)), 9) * 12
    if raw is not None and pct is not None:
        score += 1000
    if "[" in text or "]" in text:
        score += 10
    return score


def _save_ocr_debug(original, candidates, variants, best_text, engine_name):
    if not OCR_DEBUG:
        return
    try:
        OCR_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        for old in OCR_DEBUG_DIR.glob("latest_*"):
            if old.is_file():
                old.unlink()
        original.save(OCR_DEBUG_DIR / "latest_00_original.png")
        for idx, (label, candidate) in enumerate(candidates[:5], start=1):
            candidate.save(OCR_DEBUG_DIR / f"latest_{idx:02}_{label}.png")
        for idx, variant in enumerate(variants[:8], start=1):
            variant.save(OCR_DEBUG_DIR / f"latest_variant_{idx:02}.png")
        (OCR_DEBUG_DIR / "latest_result.txt").write_text(
            f"engine={engine_name}\ntext={best_text}\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def ocr_diagnostic_text(engine_name, raw, pct, source_text):
    source_text = " ".join((source_text or "").split())
    if raw is None:
        return f"{engine_name}: 未讀到 EXP"
    if raw is not None or pct is not None:
        parsed = exp_display_grouped(raw, pct)
        if source_text:
            return f"{engine_name}: 解析 {parsed}（原始 {source_text}）"
        return f"{engine_name}: 解析 {parsed}"
    return f"{engine_name}: {source_text}" if source_text else ""


def ocr_exp_detail(image: Image.Image):
    original = image.convert("RGB")
    candidates = ocr_candidate_images(original)
    variants = []
    best_text = ""
    best_engine = "PP-OCRv5（去綠條預處理）"
    best = (None, None)
    best_score = -1

    visual_pct = estimate_bar_percent(original)
    for text, confidence in ocr_texts(original):
        bracket_raw = raw_before_bracket(text)
        raw, pct = parse_ocr_text(text, visual_pct=visual_pct)
        if bracket_raw is not None:
            raw = bracket_raw
        if text and not best_text:
            best_text = text
            best_engine = "PP-OCRv5（去綠條預處理）"
        score = _ocr_score(raw, pct, text, confidence)
        if score > best_score:
            best = (raw, pct)
            best_text = text
            best_engine = "PP-OCRv5（去綠條預處理）"
            best_score = score
        if raw is not None and pct is not None and confidence >= 0.70:
            diagnostic = ocr_diagnostic_text(best_engine, best[0], best[1], best_text)
            _save_ocr_debug(image, candidates, variants, diagnostic, best_engine)
            return best[0], best[1], diagnostic

    if not best_text and _PP_OCR_ERROR:
        best_text = _PP_OCR_ERROR
        best_engine = "PP-OCRv5 初始化失敗"

    diagnostic = ocr_diagnostic_text(best_engine, best[0], best[1], best_text)
    _save_ocr_debug(image, candidates, variants, diagnostic, best_engine)
    return best[0], best[1], diagnostic


def ocr_exp(image: Image.Image):
    raw, pct, _text = ocr_exp_detail(image)
    return raw, pct


def list_windows():
    """Return [(title, window_obj), ...] for visible, non-empty-title windows."""
    out = []
    for w in pwc.getAllWindows():
        try:
            t = (w.title or "").strip()
            if not t:
                continue
            if int(w.width) <= 50 or int(w.height) <= 50:
                continue
            try:
                if w.isMinimized:
                    continue
            except Exception:
                pass
            out.append((t, w))
        except Exception:
            continue
    return out


def window_label(title, window_obj, index):
    """Human-readable label for selecting among windows, including duplicates."""
    try:
        size = f"{int(window_obj.width)}x{int(window_obj.height)}"
        pos = f"+{int(window_obj.left)}+{int(window_obj.top)}"
        return f"{index + 1}. {title} ({size} {pos})"
    except Exception:
        return f"{index + 1}. {title}"


def window_key(title, window_obj):
    """Best-effort stable key used to keep the same selection after refresh."""
    for attr in ("_hWnd", "hWnd", "handle"):
        try:
            value = getattr(window_obj, attr)
            if value:
                return ("handle", str(value))
        except Exception:
            pass
    try:
        return (
            "geometry",
            title,
            int(window_obj.left),
            int(window_obj.top),
            int(window_obj.width),
            int(window_obj.height),
        )
    except Exception:
        return ("title", title)


def window_region_key(title):
    return re.sub(r"\s+", " ", (title or "").strip()).casefold()


def validate_region(region, win=None):
    if not isinstance(region, (list, tuple)) or len(region) != 4:
        return None
    try:
        x, y, w, h = [int(v) for v in region]
    except Exception:
        return None
    if x < 0 or y < 0 or w < 8 or h < 8:
        return None
    if win is not None:
        try:
            if x + w > int(win.width) + 4 or y + h > int(win.height) + 4:
                return None
        except Exception:
            pass
    return (x, y, w, h)


def rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    radius = max(0, min(radius, int((x2 - x1) / 2), int((y2 - y1) / 2)))
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, **kwargs)


class RoundedPanel(tk.Frame):
    def __init__(self, master, bg, fill, border, radius=18, padding=14):
        super().__init__(master, bg=bg)
        self._bg = bg
        self._fill = fill
        self._border = border
        self._radius = radius
        self._padding = padding
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.content = tk.Frame(self.canvas, bg=fill)
        self._window = self.canvas.create_window(
            padding, padding, anchor="nw", window=self.content
        )
        self._rect = None
        self.bind("<Configure>", self._draw)
        self.canvas.bind("<Configure>", self._draw)
        self.content.bind("<Configure>", self._sync_requested_size)

    def _sync_requested_size(self, _event=None):
        self.canvas.configure(
            width=max(1, self.content.winfo_reqwidth() + self._padding * 2),
            height=max(1, self.content.winfo_reqheight() + self._padding * 2),
        )

    def _draw(self, _event=None):
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        self.canvas.delete("panel-bg")
        rounded_rect(
            self.canvas,
            1,
            1,
            w - 2,
            h - 2,
            self._radius,
            fill=self._fill,
            outline=self._border,
            width=1,
            tags="panel-bg",
        )
        self.canvas.tag_lower("panel-bg")
        inner_w = max(1, w - self._padding * 2)
        inner_h = max(1, h - self._padding * 2)
        self.canvas.coords(self._window, self._padding, self._padding)
        self.canvas.itemconfigure(self._window, width=inner_w, height=inner_h)


class RoundedBadge(tk.Canvas):
    def __init__(self, master, text, bg, fill, fg, radius=14, **kwargs):
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, height=30, **kwargs)
        self._outer_bg = bg
        self._fill = fill
        self._fg = fg
        self._radius = radius
        self._text = text
        self.configure(width=86)
        self.bind("<Configure>", self._draw)
        self._draw()

    def set(self, text, fill, fg):
        self._text = text
        self._fill = fill
        self._fg = fg
        self._draw()

    def _draw(self, _event=None):
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        rounded_rect(self, 1, 1, w - 2, h - 2, self._radius, fill=self._fill, outline=self._fill)
        self.create_text(w / 2, h / 2, text=self._text, fill=self._fg, font=("Microsoft JhengHei UI", 10, "bold"))


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master,
        text,
        command=None,
        bg="#0A0A0F",
        fill="#1F2937",
        fg="#E5E7EB",
        active_fill="#293548",
        disabled_fill="#111827",
        disabled_fg="#64748B",
        radius=14,
        width=132,
        height=40,
        state="normal",
    ):
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, width=width, height=height, cursor="hand2")
        self._text = text
        self._command = command
        self._fill = fill
        self._fg = fg
        self._active_fill = active_fill
        self._disabled_fill = disabled_fill
        self._disabled_fg = disabled_fg
        self._radius = radius
        self._state = state
        self.bind("<Configure>", self._draw)
        self.bind("<Enter>", lambda _e: self._draw(hover=True))
        self.bind("<Leave>", lambda _e: self._draw(hover=False))
        self.bind("<ButtonRelease-1>", self._click)
        self._draw()

    def config(self, **kwargs):
        if "state" in kwargs:
            self._state = kwargs.pop("state")
        if "text" in kwargs:
            self._text = kwargs.pop("text")
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "fill" in kwargs:
            self._fill = kwargs.pop("fill")
        if "fg" in kwargs:
            self._fg = kwargs.pop("fg")
        if "active_fill" in kwargs:
            self._active_fill = kwargs.pop("active_fill")
        if "disabled_fill" in kwargs:
            self._disabled_fill = kwargs.pop("disabled_fill")
        if "disabled_fg" in kwargs:
            self._disabled_fg = kwargs.pop("disabled_fg")
        if kwargs:
            super().config(**kwargs)
        super().configure(cursor="hand2" if self._state != "disabled" else "arrow")
        self._draw()

    configure = config

    def _click(self, _event=None):
        if self._state != "disabled" and self._command:
            self._command()

    def _draw(self, _event=None, hover=False):
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        if self._state == "disabled":
            fill = self._disabled_fill
            fg = self._disabled_fg
        else:
            fill = self._active_fill if hover else self._fill
            fg = self._fg
        rounded_rect(self, 1, 1, w - 2, h - 2, self._radius, fill=fill, outline=fill)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg, font=("Microsoft JhengHei UI", 10, "bold"))


class RoundedSelect(tk.Canvas):
    def __init__(self, master, bg, fill, border, fg, muted_fg, radius=14, height=40):
        super().__init__(master, bg=bg, highlightthickness=0, bd=0, height=height, cursor="hand2")
        self._outer_bg = bg
        self._fill = fill
        self._border = border
        self._fg = fg
        self._muted_fg = muted_fg
        self._radius = radius
        self._values = []
        self._index = -1
        self._callbacks = []
        self.configure(width=520)
        self.bind("<Configure>", self._draw)
        self.bind("<ButtonRelease-1>", self._open_popup)
        self._draw()

    def __setitem__(self, key, value):
        if key != "values":
            raise KeyError(key)
        self._values = list(value)
        if self._index >= len(self._values):
            self._index = -1
        self._draw()

    def __getitem__(self, key):
        if key != "values":
            raise KeyError(key)
        return self._values

    def bind(self, sequence=None, func=None, add=None):
        if sequence == "<<ComboboxSelected>>":
            if func:
                self._callbacks.append(func)
            return None
        return super().bind(sequence, func, add)

    def current(self, index=None):
        if index is None:
            return self._index
        self._index = index if 0 <= index < len(self._values) else -1
        self._draw()

    def set(self, value):
        if value in self._values:
            self._index = self._values.index(value)
        else:
            self._index = -1
        self._draw()

    def _selected_text(self):
        if 0 <= self._index < len(self._values):
            return self._values[self._index]
        return "請選擇視窗"

    def _draw(self, _event=None):
        self.delete("all")
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        rounded_rect(self, 1, 1, w - 2, h - 2, self._radius, fill=self._fill, outline=self._border, width=1)
        text = self._selected_text()
        fg = self._fg if self._index >= 0 else self._muted_fg
        self.create_text(14, h / 2, text=text, fill=fg, font=("Microsoft JhengHei UI", 10), anchor="w", width=max(40, w - 52))
        cx = w - 22
        cy = h / 2
        self.create_line(
            cx - 5,
            cy - 2,
            cx,
            cy + 4,
            cx + 5,
            cy - 2,
            fill=self._muted_fg,
            width=2,
            capstyle="round",
            joinstyle="round",
        )

    def _open_popup(self, _event=None):
        if not self._values:
            return
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=self._border)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        w = self.winfo_width()
        h = min(260, max(48, len(self._values) * 28 + 8))
        popup.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(popup, bg=self._fill, padx=6, pady=6)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        listbox = tk.Listbox(
            frame,
            bg=self._fill,
            fg=self._fg,
            selectbackground="#0B6B49",
            selectforeground=self._fg,
            activestyle="none",
            highlightthickness=0,
            bd=0,
            font=("Microsoft JhengHei UI", 10),
        )
        listbox.pack(fill="both", expand=True)
        for item in self._values:
            listbox.insert("end", item)
        if self._index >= 0:
            listbox.selection_set(self._index)
            listbox.see(self._index)

        def choose(_event=None):
            selection = listbox.curselection()
            if selection:
                self._index = int(selection[0])
                self._draw()
                for callback in self._callbacks:
                    callback(None)
            popup.destroy()

        listbox.bind("<ButtonRelease-1>", choose)
        listbox.bind("<Return>", choose)
        popup.bind("<Escape>", lambda _e: popup.destroy())
        popup.focus_force()


class RegionPicker(tk.Toplevel):
    """Show a zoomable snapshot of the chosen window; drag to pick the EXP region."""

    def __init__(self, master, snapshot: Image.Image, on_done, colors=None):
        super().__init__(master)
        self.title("框選 EXP 區域")
        self.on_done = on_done
        self.original = snapshot.convert("RGB")
        self.colors = colors or {
            "bg": "#0A0A0F",
            "panel": "#12131B",
            "panel_2": "#1A1D2A",
            "border": "#2A3041",
            "fg": "#F8FAFC",
            "muted_text": "#A7B3C8",
            "accent": "#00E5A8",
            "accent_dark": "#0B6B49",
            "button": "#1F2937",
        }
        self.configure(bg=self.colors["bg"])
        self._region = None
        self.start = None
        self.rect = None
        self.scale = 1.0
        self.tk_img = None
        self.image_id = None

        shell = tk.Frame(self, bg=self.colors["bg"], padx=14, pady=14)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        header = tk.Frame(shell, bg=self.colors["bg"])
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="框選 EXP 區域",
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            font=("Microsoft JhengHei UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            shell,
            text="可放大圖片後拖曳框選；捲動滑鼠可上下移動，按住 Ctrl 滾輪可縮放。",
            bg=self.colors["bg"],
            fg=self.colors["muted_text"],
            font=("Microsoft JhengHei UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        toolbar = tk.Frame(header, bg=self.colors["bg"])
        toolbar.grid(row=0, column=1, sticky="e")
        RoundedButton(toolbar, text="縮小", command=self._zoom_out, bg=self.colors["bg"], width=78, height=34).pack(side="left")
        RoundedButton(
            toolbar,
            text="100%",
            command=self._zoom_reset,
            bg=self.colors["bg"],
            fill=self.colors["button"],
            active_fill="#293548",
            width=78,
            height=34,
        ).pack(side="left", padx=(8, 0))
        RoundedButton(
            toolbar,
            text="放大",
            command=self._zoom_in,
            bg=self.colors["bg"],
            fill=self.colors["accent_dark"],
            active_fill="#0F8A5D",
            width=78,
            height=34,
        ).pack(side="left", padx=(8, 0))

        viewer = tk.Frame(shell, bg=self.colors["border"], padx=1, pady=1)
        viewer.grid(row=2, column=0, sticky="nsew")
        viewer.columnconfigure(0, weight=1)
        viewer.rowconfigure(0, weight=1)

        screen_w = max(800, self.winfo_screenwidth())
        screen_h = max(600, self.winfo_screenheight())
        canvas_w = min(self.original.width, int(screen_w * 0.86))
        canvas_h = min(self.original.height, int(screen_h * 0.64))
        canvas_w = max(640, min(canvas_w, screen_w - 120))
        canvas_h = max(360, min(canvas_h, screen_h - 220))
        self.canvas = tk.Canvas(
            viewer,
            width=canvas_w,
            height=canvas_h,
            cursor="cross",
            bg="#05070D",
            highlightthickness=0,
            bd=0,
            xscrollincrement=1,
            yscrollincrement=1,
        )
        xbar = ttk.Scrollbar(viewer, orient="horizontal", command=self.canvas.xview)
        ybar = ttk.Scrollbar(viewer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")

        self.coord_lbl = tk.Label(
            shell,
            text="尚未框選",
            bg=self.colors["bg"],
            fg=self.colors["muted_text"],
            font=("Microsoft JhengHei UI", 10),
        )
        self.coord_lbl.grid(row=3, column=0, sticky="w", pady=(10, 0))

        bar = tk.Frame(shell, bg=self.colors["bg"])
        bar.grid(row=4, column=0, sticky="e", pady=(12, 0))
        RoundedButton(
            bar,
            text="取消",
            command=self._cancel,
            bg=self.colors["bg"],
            fill=self.colors["button"],
            active_fill="#293548",
            width=86,
        ).pack(side="right", padx=(8, 0))
        self.ok_btn = RoundedButton(
            bar,
            text="確認",
            command=self._ok,
            bg=self.colors["bg"],
            fill="#0B6B49",
            active_fill="#0F8A5D",
            state="disabled",
            width=86,
        )
        self.ok_btn.pack(side="right")

        self._render_image()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<MouseWheel>", self._mousewheel)
        self.bind("<Escape>", lambda e: self._cancel())
        self.transient(master)
        self.grab_set()

    def _display_image(self):
        w = max(1, int(round(self.original.width * self.scale)))
        h = max(1, int(round(self.original.height * self.scale)))
        if self.scale == 1.0:
            return self.original
        resample = Image.Resampling.NEAREST if self.scale > 1.0 else Image.Resampling.LANCZOS
        return self.original.resize((w, h), resample)

    def _render_image(self):
        xview = self.canvas.xview()
        yview = self.canvas.yview()
        disp = self._display_image()
        self.tk_img = ImageTk.PhotoImage(disp)
        if self.image_id is None:
            self.image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        else:
            self.canvas.itemconfigure(self.image_id, image=self.tk_img)
        self.canvas.configure(scrollregion=(0, 0, disp.width, disp.height))
        if xview and yview:
            self.canvas.xview_moveto(xview[0])
            self.canvas.yview_moveto(yview[0])
        self._draw_region_rect()
        if self._region:
            x, y, w, h = self._region
            self.coord_lbl.config(
                text=f"已框選：{w}×{h} @ ({x}, {y})，目前縮放 {int(self.scale * 100)}%",
                fg=self.colors["accent"],
            )
        else:
            self.coord_lbl.config(text=f"尚未框選，目前縮放 {int(self.scale * 100)}%", fg=self.colors["muted_text"])

    def _draw_region_rect(self):
        if self.rect:
            self.canvas.delete(self.rect)
            self.rect = None
        if not self._region:
            return
        x, y, w, h = self._region
        self.rect = self.canvas.create_rectangle(
            x * self.scale,
            y * self.scale,
            (x + w) * self.scale,
            (y + h) * self.scale,
            outline="#EF4444",
            width=2,
        )

    def _set_zoom(self, scale):
        self.scale = max(REGION_PICKER_MIN_SCALE, min(REGION_PICKER_MAX_SCALE, float(scale)))
        self._render_image()

    def _zoom_in(self):
        self._set_zoom(self.scale * REGION_PICKER_ZOOM_STEP)

    def _zoom_out(self):
        self._set_zoom(self.scale / REGION_PICKER_ZOOM_STEP)

    def _zoom_reset(self):
        self._set_zoom(1.0)

    def _event_xy(self, e):
        return self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)

    def _press(self, e):
        self.start = self._event_xy(e)
        self._region = None
        if self.rect:
            self.canvas.delete(self.rect)
        x, y = self.start
        self.rect = self.canvas.create_rectangle(x, y, x, y, outline="#EF4444", width=2)
        self.ok_btn.config(state="disabled")

    def _drag(self, e):
        if self.rect and self.start:
            x0, y0 = self.start
            x1, y1 = self._event_xy(e)
            self.canvas.coords(self.rect, x0, y0, x1, y1)

    def _release(self, e):
        if not self.start:
            return
        x0, y0 = self.start
        x1, y1 = self._event_xy(e)
        if abs(x1 - x0) < 4 or abs(y1 - y0) < 4:
            self.coord_lbl.config(text="範圍太小，請重新框選", fg="#F87171")
            return
        ox = int(max(0, min(x0, x1) / self.scale))
        oy = int(max(0, min(y0, y1) / self.scale))
        ow = int(abs(x1 - x0) / self.scale)
        oh = int(abs(y1 - y0) / self.scale)
        ow = min(ow, self.original.width - ox)
        oh = min(oh, self.original.height - oy)
        self._region = (ox, oy, ow, oh)
        self.coord_lbl.config(
            text=f"已框選：{ow}×{oh} @ ({ox}, {oy})，目前縮放 {int(self.scale * 100)}%",
            fg=self.colors["accent"],
        )
        self.ok_btn.config(state="normal")

    def _mousewheel(self, e):
        if e.state & 0x0004:
            if e.delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            return "break"
        steps = int(-1 * (e.delta / 120)) if e.delta else 0
        if steps:
            self.canvas.yview_scroll(steps, "units")
        return "break"

    def _ok(self):
        self.destroy()
        self.on_done(self._region)

    def _cancel(self):
        self.destroy()
        self.on_done(None)


class CalibrationDialog(tk.Toplevel):
    """Let the user enter the true EXP and adjust the digit crop used for learning."""

    def __init__(self, master, image: Image.Image, initial_boxes, colors):
        super().__init__(master)
        self.title("校正目前 EXP")
        self.configure(bg=colors["bg"])
        self.colors = colors
        self.original = image
        self.result = None
        self._selection = None
        self._drag_start = None
        self._rect = None

        scale = min(4.0, max(1.0, min(1080 / image.width, 360 / image.height)))
        disp = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.NEAREST)
        self.scale = scale
        self.tk_img = ImageTk.PhotoImage(disp)

        shell = tk.Frame(self, bg=colors["bg"], padx=18, pady=18)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)

        tk.Label(
            shell,
            text="校準 EXP 數字",
            bg=colors["bg"],
            fg=colors["fg"],
            font=("Microsoft JhengHei UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            shell,
            text="輸入畫面上的純 EXP 數字，並拖曳框住純數字範圍。不要包含括號、百分比或 EXP 文字。",
            bg=colors["bg"],
            fg=colors["muted_text"],
            font=("Microsoft JhengHei UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        panel = RoundedPanel(shell, bg=colors["bg"], fill=colors["panel"], border=colors["border"], radius=18, padding=14)
        panel.grid(row=2, column=0, sticky="ew")
        panel.content.columnconfigure(0, weight=1)

        tk.Label(
            panel.content,
            text="正確 EXP 數字",
            bg=colors["panel"],
            fg=colors["accent_2"],
            font=("Microsoft JhengHei UI", 9),
        ).grid(row=0, column=0, sticky="w")
        entry_wrap = tk.Frame(panel.content, bg=colors["border"], padx=1, pady=1)
        entry_wrap.grid(row=1, column=0, sticky="ew", pady=(6, 12))
        self.value_entry = tk.Entry(
            entry_wrap,
            bg=colors["panel_2"],
            fg=colors["fg"],
            insertbackground=colors["fg"],
            relief="flat",
            bd=0,
            font=("Microsoft JhengHei UI", 14, "bold"),
        )
        self.value_entry.pack(fill="x", ipady=8, padx=1, pady=1)

        self.canvas = tk.Canvas(
            panel.content,
            width=disp.width,
            height=disp.height,
            bg=colors["panel_2"],
            highlightthickness=1,
            highlightbackground=colors["border"],
            cursor="cross",
        )
        self.canvas.grid(row=2, column=0, sticky="w")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.hint = tk.Label(
            panel.content,
            text="拖曳調整數字範圍後按「儲存學習」。",
            bg=colors["panel"],
            fg=colors["muted_text"],
            font=("Microsoft JhengHei UI", 9),
        )
        self.hint.grid(row=3, column=0, sticky="w", pady=(10, 0))

        bar = tk.Frame(shell, bg=colors["bg"])
        bar.grid(row=3, column=0, sticky="e", pady=(14, 0))
        RoundedButton(bar, text="取消", command=self._cancel, bg=colors["bg"], width=92).pack(side="right", padx=(8, 0))
        RoundedButton(
            bar,
            text="儲存學習",
            command=self._save,
            bg=colors["bg"],
            fill=colors["accent"],
            active_fill="#11B981",
            fg="#001B12",
            width=116,
        ).pack(side="right")

        if initial_boxes:
            x0 = min(box["x0"] for box in initial_boxes)
            y0 = min(box["y0"] for box in initial_boxes)
            x1 = max(box["x1"] for box in initial_boxes)
            y1 = max(box["y1"] for box in initial_boxes)
            self._set_selection((x0, y0, x1, y1))
            for box in initial_boxes:
                self.canvas.create_rectangle(
                    box["x0"] * scale,
                    box["y0"] * scale,
                    (box["x1"] + 1) * scale,
                    (box["y1"] + 1) * scale,
                    outline="#38BDF8",
                    width=1,
                )

        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self._cancel())
        self.transient(master)
        self.grab_set()
        self.value_entry.focus_set()

    def _to_image_area(self, x0, y0, x1, y1):
        ix0 = int(min(x0, x1) / self.scale)
        iy0 = int(min(y0, y1) / self.scale)
        ix1 = int(max(x0, x1) / self.scale)
        iy1 = int(max(y0, y1) / self.scale)
        return (
            max(0, min(self.original.width - 1, ix0)),
            max(0, min(self.original.height - 1, iy0)),
            max(0, min(self.original.width - 1, ix1)),
            max(0, min(self.original.height - 1, iy1)),
        )

    def _set_selection(self, area):
        self._selection = area
        x0, y0, x1, y1 = area
        coords = (x0 * self.scale, y0 * self.scale, (x1 + 1) * self.scale, (y1 + 1) * self.scale)
        if self._rect is None:
            self._rect = self.canvas.create_rectangle(*coords, outline="#00E0FF", width=3)
        else:
            self.canvas.coords(self._rect, *coords)
        self.canvas.tag_raise(self._rect)

    def _press(self, event):
        self._drag_start = (event.x, event.y)
        self._set_selection(self._to_image_area(event.x, event.y, event.x, event.y))

    def _drag(self, event):
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        self._set_selection(self._to_image_area(x0, y0, event.x, event.y))

    def _release(self, event):
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        area = self._to_image_area(x0, y0, event.x, event.y)
        self._drag_start = None
        if area[2] - area[0] < 4 or area[3] - area[1] < 4:
            self.hint.config(text="範圍太小，請重新拖曳純數字範圍。", fg="#FCA5A5")
            return
        self._set_selection(area)
        self.hint.config(text=f"已選擇數字範圍：{area[2] - area[0] + 1}×{area[3] - area[1] + 1}", fg=self.colors["muted_text"])

    def _save(self):
        value = re.sub(r"\D+", "", self.value_entry.get())
        if not value:
            messagebox.showwarning("需要數字", "請輸入畫面上的純 EXP 數字。", parent=self)
            return
        if self._selection is None:
            messagebox.showwarning("需要範圍", "請拖曳框住純 EXP 數字範圍。", parent=self)
            return
        self.result = (value, self._selection)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class ExpTracker:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(APP_TITLE)
        set_app_icon(root)
        root.geometry("1280x860")
        root.minsize(1120, 820)

        self.window_obj = None
        self._win_size = None
        self._wins = []
        self._selected_window_key = None
        self._settings = self._load_settings()
        self.sample_interval = self._load_sample_interval()
        _set_digit_templates(
            self._settings.get("digit_templates", {}),
            self._settings.get("trusted_digit_templates", {}),
        )
        _set_manual_digit_calibration(
            self._settings.get("last_digit_area"),
            self._settings.get("last_digit_count"),
        )
        self._manual_level = self._load_manual_level()
        self.exp_offset = None  # (x, y, w, h) relative to window's top-left
        self.samples = deque()
        self.total_gained = 0
        self._last_raw = None
        self._last_pct = None
        self._estimated_level = None
        self._level_estimate_error = None
        self._pending_raw = None
        self._pending_pct = None
        self._pending_at = None
        self._pending_jump_raw = None
        self._pending_jump_pct = None
        self._pending_jump_at = None
        self._manual_exp_floor_raw = None
        self._manual_exp_floor_level = None
        self._level_cap = None
        if self._manual_level is not None:
            self._estimated_level = self._manual_level
            self._level_estimate_error = 0.0
            self._level_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        self._ignored_samples = 0
        self._level_ups = 0
        self._learned_templates = 0
        self._capture_count = 0
        self._recognized_count = 0
        self._last_ocr_text = ""
        self._last_ocr_at = None
        self._last_error = ""
        self.session_start = None
        self.running = False
        self._compact_mode = False
        self._full_geometry = None
        self._geometry_save_after = None
        self._restoring_geometry = False
        self.compact_frame = None

        self._build_ui()
        self._refresh_level_label()
        self._apply_saved_geometry("full")
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._refresh_windows()

    def _build_ui(self):
        self._setup_style()

        c = self.colors
        f = tk.Frame(self.root, bg=c["bg"], padx=18, pady=18)
        self.main_frame = f
        f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        header = tk.Frame(f, bg=c["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)
        tk.Label(
            header,
            text=APP_NAME,
            bg=c["bg"],
            fg=c["fg"],
            font=("Microsoft JhengHei UI", 20, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="即時辨識經驗值、追蹤效率與升等進度",
            bg=c["bg"],
            fg=c["muted_text"],
            font=("Microsoft JhengHei UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))
        RoundedButton(
            header,
            text="使用說明",
            command=self._show_help,
            bg=c["bg"],
            fill=c["button"],
            active_fill="#293548",
            width=112,
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(0, 96))
        self.live_lbl = RoundedBadge(
            header,
            text="待命",
            bg=c["bg"],
            fill=c["panel_2"],
            fg=c["muted_text"],
        )
        self.live_lbl.grid(row=0, column=1, rowspan=2, sticky="e")

        top = tk.Frame(f, bg=c["bg"])
        top.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        top.columnconfigure(0, weight=3, minsize=650)
        top.columnconfigure(1, weight=2, minsize=420)
        top.rowconfigure(0, weight=1)

        target = self._panel(top, "目標視窗")
        target.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        target.columnconfigure(0, weight=1)

        tk.Label(target, text="擷取來源", bg=c["panel"], fg=c["muted_text"], font=("Microsoft JhengHei UI", 9, "bold")).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        row = tk.Frame(target, bg=c["panel"])
        row.grid(row=2, column=0, columnspan=3, sticky="ew")
        row.columnconfigure(0, weight=1)
        self.win_var = tk.StringVar()
        self.win_combo = RoundedSelect(
            row,
            bg=c["panel"],
            fill=c["panel_2"],
            border=c["border"],
            fg=c["fg"],
            muted_fg=c["muted_text"],
        )
        self.win_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.win_combo.bind("<<ComboboxSelected>>", self._on_window_selected)
        RoundedButton(
            row,
            text="重新整理",
            command=self._refresh_windows,
            bg=c["panel"],
            fill=c["button"],
            active_fill="#293548",
            width=110,
        ).grid(row=0, column=1)

        row2 = tk.Frame(target, bg=c["panel"])
        row2.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        RoundedButton(
            row2,
            text="框選 EXP 區域",
            command=self._use_window,
            bg=c["panel"],
            fill=c["accent_dark"],
            active_fill="#0F8A5D",
            width=150,
        ).pack(side="left")
        RoundedButton(
            row2,
            text="重新框選",
            command=self._use_window,
            bg=c["panel"],
            fill=c["button"],
            active_fill="#293548",
            width=116,
        ).pack(side="left", padx=(8, 0))
        RoundedButton(
            row2,
            text="校正目前 EXP",
            command=self._calibrate_digits,
            bg=c["panel"],
            fill=c["button"],
            active_fill="#293548",
            width=132,
        ).pack(side="left", padx=(8, 0))
        RoundedButton(
            row2,
            text="校正等級",
            command=self._calibrate_level,
            bg=c["panel"],
            fill=c["button"],
            active_fill="#293548",
            width=104,
        ).pack(side="left", padx=(8, 0))
        RoundedButton(
            row2,
            text="清除設定",
            command=self._clear_settings,
            bg=c["panel"],
            fill="#7F1D1D",
            fg="#FFFFFF",
            active_fill="#B91C1C",
            width=116,
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            target,
            text="更新頻率",
            bg=c["panel"],
            fg=c["muted_text"],
            font=("Microsoft JhengHei UI", 9, "bold"),
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(14, 6))
        freq_row = tk.Frame(target, bg=c["panel"])
        freq_row.grid(row=5, column=0, columnspan=3, sticky="ew")
        self.interval_buttons = {}
        for idx, seconds in enumerate(SAMPLE_INTERVAL_OPTIONS):
            btn = RoundedButton(
                freq_row,
                text=f"{seconds} 秒",
                command=lambda value=seconds: self._set_sample_interval(value),
                bg=c["panel"],
                fill=c["panel_2"],
                fg=c["muted_text"],
                active_fill="#293548",
                width=68,
                height=36,
            )
            btn.pack(side="left", padx=(0 if idx == 0 else 8, 0))
            self.interval_buttons[seconds] = btn
        self._refresh_interval_buttons()

        self.region_lbl = tk.Label(target, text="尚未設定 EXP 區域", bg=c["panel"], fg=c["muted_text"], font=("Microsoft JhengHei UI", 9))
        self.region_lbl.grid(row=6, column=0, columnspan=3, sticky="w", pady=(14, 0))

        bar = tk.Frame(target, bg=c["panel"])
        bar.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        self.start_btn = RoundedButton(
            bar,
            text="開始追蹤",
            command=self.start,
            bg=c["panel"],
            fill=c["accent"],
            fg="#03130C",
            active_fill="#38F2AA",
            state="disabled",
            width=124,
        )
        self.start_btn.pack(side="left")
        self.stop_btn = RoundedButton(
            bar,
            text="停止",
            command=self.stop,
            bg=c["panel"],
            fill=c["button"],
            active_fill="#293548",
            state="disabled",
            width=92,
        )
        self.stop_btn.pack(side="left", padx=(8, 0))
        RoundedButton(
            bar,
            text="重置",
            command=self.reset,
            bg=c["panel"],
            fill=c["button"],
            active_fill="#293548",
            width=92,
        ).pack(side="left", padx=(8, 0))
        self.compact_btn = RoundedButton(
            bar,
            text="縮小視窗",
            command=self._show_compact_window,
            bg=c["panel"],
            fill=c["button"],
            active_fill="#293548",
            state="disabled",
            width=108,
        )
        self.compact_btn.pack(side="left", padx=(8, 0))

        stats = tk.Frame(f, bg=c["bg"])
        stats.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        stats.columnconfigure(0, weight=3)
        stats.columnconfigure(1, weight=2)
        stats.rowconfigure(0, weight=1)

        current = self._panel(stats, "目前經驗值")
        current.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        current.columnconfigure(0, weight=1)

        self.cur_lbl = tk.Label(
            current,
            text="目前 EXP：—",
            bg=c["panel"],
            fg=c["accent"],
            font=("Consolas", 24, "bold"),
        )
        self.cur_lbl.grid(row=1, column=0, sticky="w", pady=(0, 16))
        meta = tk.Frame(current, bg=c["panel"])
        meta.grid(row=2, column=0, sticky="ew")
        meta.columnconfigure((0, 1, 2, 3), weight=1)
        self.elapsed_lbl = self._metric(meta, "累計時間", "00:00:00", 0)
        self.gained_lbl = self._metric(meta, "本次累積 EXP", "0", 1)
        self.rate_lbl = self._metric(meta, "近 5 分速率", "—", 2)
        self.level_lbl = self._metric(meta, "目前等級", "—", 3)

        estimate = self._panel(stats, "依近 5 分鐘預估")
        estimate.grid(row=0, column=1, sticky="nsew")
        estimate.columnconfigure(0, weight=1)
        self.eta5 = self._projection_row(estimate, "5 分鐘", "—", 1)
        self.eta10 = self._projection_row(estimate, "10 分鐘", "—", 2)
        self.eta30 = self._projection_row(estimate, "30 分鐘", "—", 3)
        self.eta_level = self._projection_row(estimate, "升級時間", "—", 4)

        diag = self._panel(top, "OCR 診斷")
        diag.grid(row=0, column=1, sticky="nsew")
        diag.columnconfigure(0, weight=1)
        diag.rowconfigure(3, weight=1)
        device_box = RoundedPanel(diag, bg=c["panel"], fill=c["panel_2"], border=c["border"], radius=14, padding=8)
        device_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        device_inner = device_box.content
        device_inner.columnconfigure(1, weight=1)
        tk.Label(
            device_inner,
            text="運算裝置",
            bg=c["panel_2"],
            fg=c["muted_text"],
            font=("Microsoft JhengHei UI", 8, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.ocr_device_lbl = tk.Label(
            device_inner,
            text=ocr_device_status(),
            bg=c["panel_2"],
            fg=c["accent"],
            font=("Consolas", 10, "bold"),
            anchor="e",
        )
        self.ocr_device_lbl.grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.ocr_lbl = tk.Label(
            diag,
            text="尚未開始取樣",
            bg=c["panel"],
            fg=c["fg"],
            font=("Microsoft JhengHei UI", 10),
            anchor="w",
            justify="left",
        )
        self.ocr_lbl.grid(row=2, column=0, sticky="ew")
        self.ocr_text_box = RoundedPanel(diag, bg=c["panel"], fill=c["panel_2"], border=c["border"], radius=14, padding=8)
        self.ocr_text_box.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        self.ocr_text_lbl = tk.Label(
            self.ocr_text_box.content,
            text="最後讀取：—",
            bg=c["panel_2"],
            fg=c["muted_text"],
            font=("Consolas", 10),
            anchor="nw",
            justify="left",
        )
        self.ocr_text_lbl.pack(fill="both", expand=True)

        footer = tk.Frame(f, bg=c["bg"])
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        self.status = tk.Label(footer, text="", bg=c["bg"], fg=c["muted_text"], font=("Microsoft JhengHei UI", 9), anchor="w")
        self.status.grid(row=0, column=0, sticky="ew")
        tk.Label(
            footer,
            text=APP_AUTHOR,
            bg=c["bg"],
            fg=c["muted_text"],
            font=("Microsoft JhengHei UI", 9, "bold"),
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(12, 0))
        self._build_compact_ui()

    def _build_compact_ui(self):
        c = self.colors
        frame = tk.Frame(self.root, bg=c["bg"], padx=14, pady=14)
        self.compact_frame = frame
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        header = tk.Frame(frame, bg=c["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        tk.Label(
            header,
            text="精簡追蹤",
            bg=c["bg"],
            fg=c["fg"],
            font=("Microsoft JhengHei UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")
        RoundedButton(
            header,
            text="完整視窗",
            command=self._show_full_window,
            bg=c["bg"],
            fill=c["button"],
            active_fill="#293548",
            width=104,
            height=36,
        ).grid(row=0, column=1, sticky="e")

        panel = RoundedPanel(frame, bg=c["bg"], fill=c["panel"], border=c["border"], radius=18, padding=12)
        panel.grid(row=1, column=0, sticky="nsew")
        body = panel.content
        body.columnconfigure(1, weight=1)
        self.compact_current_lbl = self._compact_metric(body, "目前 EXP", "—", 0)
        self.compact_rate_lbl = self._compact_metric(body, "近 5 分速率", "—", 1)
        self.compact_eta5_lbl = self._compact_metric(body, "預估 5 分鐘", "—", 2)
        self.compact_eta30_lbl = self._compact_metric(body, "預估 30 分鐘", "—", 3)
        self.compact_level_lbl = self._compact_metric(body, "預估升級", "—", 4)

    def _compact_metric(self, parent, label, value, row):
        c = self.colors
        tk.Label(
            parent,
            text=label,
            bg=c["panel"],
            fg=c["muted_text"],
            font=("Microsoft JhengHei UI", 9, "bold"),
        ).grid(row=row, column=0, sticky="w", pady=(0 if row == 0 else 10, 0))
        value_lbl = tk.Label(
            parent,
            text=value,
            bg=c["panel"],
            fg=c["accent"],
            font=("Consolas", 18, "bold"),
            anchor="e",
        )
        value_lbl.grid(row=row, column=1, sticky="e", padx=(18, 0), pady=(0 if row == 0 else 10, 0))
        return value_lbl

    def _show_compact_window(self):
        if not self.running:
            return
        if self._compact_mode:
            return
        self._save_current_geometry("full")
        self._compact_mode = True
        self._full_geometry = self._settings.get("full_geometry") or self.root.geometry()
        self.main_frame.pack_forget()
        self.root.attributes("-topmost", True)
        self.root.minsize(380, 270)
        self._apply_saved_geometry("compact", fallback="430x310")
        self.compact_frame.pack(fill="both", expand=True)
        self._update_compact_stats()

    def _show_full_window(self):
        if not self._compact_mode:
            return
        self._save_current_geometry("compact")
        self._compact_mode = False
        if self.compact_frame:
            self.compact_frame.pack_forget()
        self.root.attributes("-topmost", False)
        self.root.minsize(980, 820)
        self.main_frame.pack(fill="both", expand=True)
        self._apply_saved_geometry("full", fallback=self._full_geometry or "1020x880")

    def _valid_geometry(self, geometry):
        if not isinstance(geometry, str):
            return None
        if re.fullmatch(r"\d+x\d+(?:[+-]\d+[+-]\d+)?", geometry):
            return geometry
        return None

    def _geometry_key(self, mode=None):
        if mode is None:
            mode = "compact" if self._compact_mode else "full"
        return "compact_geometry" if mode == "compact" else "full_geometry"

    def _apply_saved_geometry(self, mode, fallback=None):
        geometry = self._valid_geometry(self._settings.get(self._geometry_key(mode)))
        if geometry is None:
            geometry = self._valid_geometry(fallback)
        if geometry is None:
            return
        self._restoring_geometry = True
        try:
            self.root.geometry(geometry)
        finally:
            self.root.after(250, lambda: setattr(self, "_restoring_geometry", False))

    def _save_current_geometry(self, mode=None):
        if self._restoring_geometry:
            return
        geometry = self.root.geometry()
        if not self._valid_geometry(geometry):
            return
        key = self._geometry_key(mode)
        if self._settings.get(key) == geometry:
            return
        self._settings[key] = geometry
        self._save_settings()

    def _on_root_configure(self, event):
        if event.widget is not self.root or self._restoring_geometry:
            return
        if self._geometry_save_after is not None:
            self.root.after_cancel(self._geometry_save_after)
        self._geometry_save_after = self.root.after(700, self._save_configured_geometry)

    def _save_configured_geometry(self):
        self._geometry_save_after = None
        self._save_current_geometry()

    def _on_close(self):
        if self._geometry_save_after is not None:
            try:
                self.root.after_cancel(self._geometry_save_after)
            except Exception:
                pass
            self._geometry_save_after = None
        self._save_current_geometry()
        self.root.destroy()

    def _setup_style(self):
        self.colors = {
            "bg": "#0A0A0F",
            "panel": "#12121A",
            "panel_2": "#1A1B25",
            "border": "#2A2A3A",
            "fg": "#E5E7EB",
            "muted_text": "#94A3B8",
            "accent": "#00E38A",
            "accent_dark": "#0B6B49",
            "accent_2": "#00D4FF",
            "danger": "#FF3366",
            "button": "#1F2937",
        }
        c = self.colors
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.root.configure(bg=c["bg"])
        style.configure("TButton", font=("Microsoft JhengHei UI", 10, "bold"), padding=(14, 8), borderwidth=0)
        style.configure("Primary.TButton", background=c["accent"], foreground="#03130C")
        style.map("Primary.TButton", background=[("active", "#38F2AA"), ("disabled", "#1F2937")], foreground=[("disabled", "#64748B")])
        style.configure("Accent.TButton", background=c["accent_dark"], foreground=c["fg"])
        style.map("Accent.TButton", background=[("active", "#0F8A5D")])
        style.configure("Ghost.TButton", background=c["button"], foreground=c["fg"])
        style.map("Ghost.TButton", background=[("active", "#293548"), ("disabled", "#111827")], foreground=[("disabled", "#64748B")])
        style.configure(
            "TCombobox",
            fieldbackground=c["panel_2"],
            background=c["panel_2"],
            foreground=c["fg"],
            arrowcolor=c["accent"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
            padding=6,
        )

    def _panel(self, parent, title):
        c = self.colors
        panel = RoundedPanel(parent, bg=c["bg"], fill=c["panel"], border=c["border"], radius=18, padding=14)
        inner = panel.content
        inner.grid = panel.grid
        inner.grid_remove = panel.grid_remove
        inner.grid_forget = panel.grid_forget
        tk.Label(
            inner,
            text=title,
            bg=c["panel"],
            fg=c["accent_2"],
            font=("Microsoft JhengHei UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        inner.columnconfigure(0, weight=1)
        return inner

    def _metric(self, parent, label, value, col):
        c = self.colors
        panel = RoundedPanel(parent, bg=c["panel"], fill=c["panel_2"], border=c["border"], radius=14, padding=10)
        panel.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        frame = panel.content
        tk.Label(frame, text=label, bg=c["panel_2"], fg=c["muted_text"], font=("Microsoft JhengHei UI", 8, "bold")).pack(anchor="w")
        value_lbl = tk.Label(frame, text=value, bg=c["panel_2"], fg=c["fg"], font=("Consolas", 13, "bold"))
        value_lbl.pack(anchor="w", pady=(4, 0))
        return value_lbl

    def _projection_row(self, parent, label, value, row):
        c = self.colors
        frame = tk.Frame(parent, bg=c["panel"], pady=5)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        frame.columnconfigure(1, weight=1)
        tk.Label(frame, text=label, bg=c["panel"], fg=c["muted_text"], font=("Consolas", 9, "bold")).grid(row=0, column=0, sticky="w")
        value_lbl = tk.Label(frame, text=value, bg=c["panel"], fg=c["accent"], font=("Consolas", 15, "bold"))
        value_lbl.grid(row=0, column=1, sticky="e")
        return value_lbl

    def _load_settings(self):
        try:
            if SETTINGS_PATH.exists():
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data.setdefault("regions", {})
                    return data
        except Exception:
            pass
        return {"regions": {}}

    def _valid_sample_interval(self, value):
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return DEFAULT_SAMPLE_INTERVAL
        if seconds in SAMPLE_INTERVAL_OPTIONS:
            return seconds
        return DEFAULT_SAMPLE_INTERVAL

    def _load_sample_interval(self):
        return self._valid_sample_interval(self._settings.get("sample_interval", DEFAULT_SAMPLE_INTERVAL))

    def _valid_manual_level(self, value):
        try:
            level = int(value)
        except (TypeError, ValueError):
            return None
        if MIN_MAPLESTAR_LEVEL <= level <= MAX_MAPLESTAR_LEVEL:
            return level
        return None

    def _load_manual_level(self):
        return self._valid_manual_level(self._settings.get("manual_level"))

    def _set_manual_level(self, level):
        self._manual_level = self._valid_manual_level(level)
        if self._manual_level is None:
            self._settings.pop("manual_level", None)
        else:
            self._settings["manual_level"] = self._manual_level
        self._save_settings()
        if self._manual_level is not None:
            self._estimated_level = self._manual_level
            self._level_estimate_error = 0.0
            self._level_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        self._refresh_level_label()

    def _advance_manual_level(self):
        if self._manual_level is None:
            return
        next_level = self._valid_manual_level(self._manual_level + 1)
        if next_level is None:
            return
        self._manual_level = next_level
        self._settings["manual_level"] = next_level
        self._save_settings()
        self._estimated_level = next_level
        self._level_estimate_error = 0.0
        self._level_cap = float(MAPLESTAR_EXP_BY_LEVEL[next_level])
        self._manual_exp_floor_raw = None
        self._manual_exp_floor_level = None
        self._refresh_level_label()

    def _refresh_level_label(self):
        if hasattr(self, "level_lbl"):
            self.level_lbl.config(text=self._level_display_text())

    def _refresh_interval_buttons(self):
        if not hasattr(self, "interval_buttons"):
            return
        for seconds, button in self.interval_buttons.items():
            selected = seconds == self.sample_interval
            button.config(
                fill=self.colors["accent_dark"] if selected else self.colors["panel_2"],
                fg=self.colors["fg"] if selected else self.colors["muted_text"],
                active_fill="#0F8A5D" if selected else "#293548",
            )

    def _set_sample_interval(self, seconds):
        self.sample_interval = self._valid_sample_interval(seconds)
        self._settings["sample_interval"] = self.sample_interval
        self._save_settings()
        self._refresh_interval_buttons()
        self.status.config(text=f"更新頻率已改為每 {self.sample_interval} 秒取樣一次")

    def _save_settings(self):
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(
                json.dumps(self._settings, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            self.status.config(text=f"設定儲存失敗：{e}")

    def _clear_settings(self):
        ok = messagebox.askyesno(
            "確認清除設定",
            "確定要清除所有設定資料嗎？\n\n"
            "這會刪除：\n"
            "- 已記住的視窗與 EXP 框選位置\n"
            "- 已記住的手動校正資料\n"
            "- 已記住的目前等級校正\n"
            "- 已記住的更新頻率\n"
            "- 已記住的完整視窗與精簡視窗大小\n\n"
            "本次累積與目前追蹤狀態也會重置。",
            icon="warning",
            parent=self.root,
        )
        if not ok:
            return

        self.stop()
        self._settings = {"regions": {}}
        self.sample_interval = DEFAULT_SAMPLE_INTERVAL
        self._manual_level = None
        self._refresh_interval_buttons()
        self._refresh_level_label()
        _set_digit_templates({}, {})
        _set_manual_digit_calibration(None, None)
        self.exp_offset = None
        self.window_obj = None
        self._win_size = None
        self._selected_window_key = None
        try:
            if SETTINGS_PATH.exists():
                SETTINGS_PATH.unlink()
        except Exception as e:
            messagebox.showerror("清除失敗", f"無法刪除設定檔：{e}", parent=self.root)
            return

        self.reset()
        self.region_lbl.config(text="尚未設定 EXP 區域", foreground=self.colors["muted_text"])
        self.start_btn.config(state="disabled")
        self.status.config(text="已清除設定資料，請重新選擇視窗、框選 EXP 區域並校正目前 EXP")
        messagebox.showinfo("清除完成", "設定資料已清除。", parent=self.root)

    def _saved_region_for_window(self, title, win):
        regions = self._settings.get("regions", {})
        region = validate_region(regions.get(window_region_key(title)), win)
        if region is not None:
            return region
        if "Maple" in (title or "") or "楓" in (title or ""):
            return validate_region(self._settings.get("last_region"), win)
        return None

    def _apply_region(self, region, saved=False):
        region = validate_region(region, self.window_obj)
        if not region:
            return False
        self.exp_offset = region
        x, y, w, h = region
        prefix = "已載入上次 EXP 區域" if saved else "EXP 區域"
        self.region_lbl.config(
            text=f"{prefix}：{w}×{h} @ ({x}, {y}) (相對視窗)",
            foreground=self.colors["accent"],
        )
        self.start_btn.config(state="normal")
        return True

    def _save_region_for_selected_window(self):
        idx = self.win_combo.current()
        if idx < 0 or idx >= len(getattr(self, "_wins", [])) or not self.exp_offset:
            return
        title, _win = self._wins[idx]
        region = [int(v) for v in self.exp_offset]
        self._settings.setdefault("regions", {})[window_region_key(title)] = region
        self._settings["last_region"] = region
        self._settings["last_window_title"] = title
        self._save_settings()

    def _apply_saved_region_for_selected_window(self):
        idx = self.win_combo.current()
        if idx < 0 or idx >= len(getattr(self, "_wins", [])):
            return False
        title, win = self._wins[idx]
        region = self._saved_region_for_window(title, win)
        if region is None:
            if not self.running:
                self.exp_offset = None
                self.window_obj = None
                self.region_lbl.config(
                    text="尚未設定 EXP 區域",
                    foreground=self.colors["muted_text"],
                )
                self.start_btn.config(state="disabled")
            return False
        self.window_obj = win
        try:
            self._win_size = (int(win.width), int(win.height))
        except Exception:
            self._win_size = None
        return self._apply_region(region, saved=True)

    def _refresh_windows(self):
        if pwc is None:
            messagebox.showerror("缺少套件", "未安裝 pywinctl，請先執行：pip install pywinctl")
            return
        previous_key = self._selected_window_key
        selected_idx = self.win_combo.current()
        if 0 <= selected_idx < len(getattr(self, "_wins", [])):
            previous_key = window_key(*self._wins[selected_idx])

        self._wins = list_windows()
        labels = [window_label(t, w, i) for i, (t, w) in enumerate(self._wins)]
        self.win_combo["values"] = labels
        if not labels:
            self.win_combo.set("")
            self._selected_window_key = None
            self.status.config(text="找不到可選擇的視窗")
            return

        keys = [window_key(t, w) for t, w in self._wins]
        if previous_key in keys:
            self.win_combo.current(keys.index(previous_key))
        else:
            maple_idx = next(
                (
                    i
                    for i, (t, _) in enumerate(self._wins)
                    if any(k in t for k in ("MapleStory", "Maple", "楓", "메이플"))
                ),
                0,
            )
            self.win_combo.current(maple_idx)
        self._remember_selected_window()
        loaded_region = self._apply_saved_region_for_selected_window()
        suffix = "，已套用上次框選區域" if loaded_region else ""
        self.status.config(text=f"已載入 {len(labels)} 個可選擇視窗{suffix}")

    def _remember_selected_window(self):
        idx = self.win_combo.current()
        if idx < 0 or idx >= len(getattr(self, "_wins", [])):
            self._selected_window_key = None
            return None
        title, win = self._wins[idx]
        self._selected_window_key = window_key(title, win)
        return win

    def _on_window_selected(self, _event=None):
        self._remember_selected_window()
        if self._apply_saved_region_for_selected_window():
            self.status.config(text="已套用此視窗的上次框選區域")

    def _selected_window(self):
        idx = self.win_combo.current()
        if idx < 0 or idx >= len(getattr(self, "_wins", [])):
            return None
        return self._wins[idx][1]

    def _capture_window_image(self, win):
        try:
            if hasattr(win, "activate"):
                win.activate()
                time.sleep(0.3)
        except Exception:
            pass
        with mss.mss() as sct:
            box = {
                "left": int(win.left),
                "top": int(win.top),
                "width": int(win.width),
                "height": int(win.height),
            }
            shot = sct.grab(box)
            return Image.frombytes("RGB", shot.size, shot.rgb), box

    def _use_window(self):
        win = self._selected_window()
        if not win:
            messagebox.showwarning("提示", "請先選擇一個視窗")
            return
        try:
            img, box = self._capture_window_image(win)
        except Exception as e:
            messagebox.showerror("擷取失敗", f"無法擷取此視窗：{e}")
            return
        self._remember_selected_window()
        self.window_obj = win
        self._win_size = (box["width"], box["height"])
        self.status.config(text=f"已選取：{(win.title or '')}")
        RegionPicker(self.root, img, self._on_region, self.colors)

    def _on_region(self, region):
        if not region:
            return
        if self._apply_region(region, saved=False):
            self._save_region_for_selected_window()
            self.status.config(text="已儲存框選區域，下次會自動套用")

    def _show_help(self):
        c = self.colors
        win = tk.Toplevel(self.root)
        win.title(f"使用說明 - {APP_TITLE}")
        win.configure(bg=c["bg"])
        win.geometry("720x680")
        win.minsize(640, 560)
        win.transient(self.root)

        shell = tk.Frame(win, bg=c["bg"], padx=18, pady=18)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        top = tk.Frame(shell, bg=c["bg"])
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        top.columnconfigure(0, weight=1)
        tk.Label(
            top,
            text=f"{APP_NAME} 使用說明",
            bg=c["bg"],
            fg=c["fg"],
            font=("Microsoft JhengHei UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        RoundedButton(
            top,
            text="關閉",
            command=win.destroy,
            bg=c["bg"],
            fill=c["button"],
            active_fill="#293548",
            width=82,
        ).grid(row=0, column=1, sticky="e")

        body = RoundedPanel(shell, bg=c["bg"], fill=c["panel"], border=c["border"], radius=18, padding=16)
        body.grid(row=1, column=0, sticky="nsew")
        body.content.rowconfigure(0, weight=1)
        body.content.columnconfigure(0, weight=1)

        text = tk.Text(
            body.content,
            bg=c["panel"],
            fg=c["fg"],
            insertbackground=c["fg"],
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Microsoft JhengHei UI", 10),
            padx=4,
            pady=4,
            spacing1=4,
            spacing3=8,
        )
        text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(body.content, orient="vertical", command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        text.configure(yscrollcommand=scroll.set)

        help_text = """快速開始
1. 先開啟遊戲，讓 EXP 條完整顯示在畫面上。
2. 在「擷取來源」選擇 MapleStory 視窗。
3. 按「框選 EXP 區域」，只框住 EXP 條與右側經驗值數字，不要框到 HP、MP 或其他 UI。
4. 依需要選擇「更新頻率」，可選每 1、2、3、5、10 秒取樣一次。
5. 框選後會自動記住位置，下次選到同一個視窗會自動套用。
6. 若目前 EXP 顯示不正確，可按「校正目前 EXP」手動校正目前值。
7. 若程式推估等級不符合角色實際等級，可按「校正等級」輸入目前等級。

校正目前 EXP
校準只用來手動校正目前 EXP，不會訓練或切換 OCR。後續辨識固定只使用 PP-OCRv5。

校準方式：
1. 先確認 EXP 區域已框選。
2. 讓畫面上的 EXP 數字清楚、不要被其他視窗遮住。
3. 按「校正目前 EXP」。
4. 依照畫面輸入目前 EXP 的純數字，例如畫面是 3749888[54.41%]，就只輸入 3749888。
5. 程式會把目前 EXP 改成你輸入的數字，並依照上一筆差額同步修正累積 EXP、近 5 分速率與效率預估。

校準建議：
- 如果 PP-OCRv5 偶爾讀錯，先停止並輸入正確目前 EXP 校正基準。
- 校正目前 EXP 後，同一等級內不會接受低於校正值的 OCR 讀值；只有偵測到升級歸零才會解除這個下限。
- 如果你改變遊戲縮放、解析度、UI 大小，建議重新框選 EXP 區域。

校正等級
1. 如果你已知角色目前等級，例如 Lv105，按「校正等級」並輸入 105。
2. 校正後程式會優先使用該等級的官方總 EXP 作為升級時間與異常判斷基準。
3. 偵測到升級後，手動校正的等級會自動加 1。
4. 這不會重置目前 EXP、累積 EXP、時間或效率。

開始追蹤
1. 校準完成後按「開始追蹤」。
2. 程式會先等待穩定讀值建立基準，所以剛開始幾秒鐘可能不會立刻顯示累積效率。
3. 追蹤中請盡量不要移動遊戲視窗或遮住 EXP 區域。
4. 升級後 EXP 歸零時，程式會依照上一個可靠基準估算跨級累積。
5. 追蹤中也可以調整更新頻率，新的秒數會在下一次取樣後生效。
6. 按「縮小視窗」可切到精簡追蹤，顯示目前 EXP、近 5 分速率、5 分鐘、30 分鐘與升級時間預估。

效率預估
-「近 5 分速率」不是本次總平均，而是最近 5 分鐘的滾動速率。
- 近 5 分速率會排除明顯偏離中位數的瞬間跳點，避免一次 OCR 高讀把預估撐爆。
- 本次累積 EXP 也有保護：單次 EXP 跳動過大時，必須同時符合校正等級的經驗表與進度百分比；就算連續高讀，只要和進度不一致也不會加進累積。
-「依近 5 分鐘預估」會用近 5 分速率推算 5、10、30 分鐘與升級時間；如果剛升級或剛校正，會和「本次累積 EXP ÷ 累計時間」不同。
7. 精簡追蹤會固定在所有視窗最上層；完整視窗與精簡視窗調整後的大小會分開記住。

數字跳動或沒有資料時
- 先按「停止」，確認遊戲畫面上的 EXP 數字清楚可見。
- 按「重新框選」，讓範圍只包含 EXP 條與右側數字。
- 再按「校正目前 EXP」，輸入畫面上的純 EXP 數字校正目前值。
- 重新開始追蹤。

框選範圍建議
- 要包含完整綠色 EXP 條，因為程式會用進度條輔助判斷是否異常。
- 要包含右側完整 EXP 數字。
- 不需要框 HP、MP、角色、地圖或聊天視窗。
- 不要只框數字，否則升級與異常判斷會變弱。

OCR 診斷
-「PP-OCRv5」代表目前唯一使用的 OCR 引擎。
-「已忽略異常」代表程式判斷該次讀值不可信，沒有放進累積計算。
- 當進度條接近右側數字時，程式會依照 EXP 位數動態提早進入保護判斷；若讀值明顯偏離已建立基準，會保留上一筆可信值，避免錯字污染累積。
- 程式內建 2026-04-02 更新後 Lv 10-199 經驗表，會用目前 EXP 與百分比推估等級，並優先使用表格中的本級總 EXP 估算升級時間。
"""
        text.insert("1.0", help_text)
        text.configure(state="disabled")
        win.bind("<Escape>", lambda _event: win.destroy())

    def _capture_exp_region(self):
        win = self.window_obj or self._selected_window()
        if not win or not self.exp_offset:
            return None
        try:
            wx, wy = int(win.left), int(win.top)
        except Exception:
            wx, wy = 0, 0
        ox, oy, ow, oh = self.exp_offset
        region = {"left": wx + ox, "top": wy + oy, "width": ow, "height": oh}
        with mss.mss() as sct:
            shot = sct.grab(region)
            return Image.frombytes("RGB", shot.size, shot.rgb)

    def _calibrate_digits(self):
        if not self.exp_offset:
            messagebox.showwarning("需要 EXP 區域", "請先框選 EXP 區域，再校正目前 EXP。")
            return
        image = self._capture_exp_region()
        if image is None:
            messagebox.showwarning("需要視窗", "請先選擇目標視窗。")
            return
        visual_pct = estimate_bar_percent(image)
        value = simpledialog.askstring(
            "校正目前 EXP",
            "請輸入畫面上目前 EXP 的純數字。\n這只會校正目前 EXP，不會影響 OCR 引擎。",
            parent=self.root,
        )
        if value is None:
            return
        value = re.sub(r"\D+", "", value)
        if not value:
            messagebox.showerror("校正失敗", "請輸入目前 EXP 的純數字。")
            return

        raw_value = int(value)
        self._apply_manual_exp_correction(raw_value, visual_pct)
        self.status.config(text="已校正目前 EXP；辨識來源固定為 PP-OCRv5")
        messagebox.showinfo(
            "校準完成",
            f"目前 EXP 已校正為 {raw_value:,}。\n"
            "累積 EXP、當前速率與效率預估已同步修正。\n"
            "後續辨識只會使用 PP-OCRv5。",
        )

    def _calibrate_level(self):
        current = str(self._manual_level or self._estimated_level or "")
        value = simpledialog.askstring(
            "校正目前等級",
            f"請輸入目前角色等級（{MIN_MAPLESTAR_LEVEL} 到 {MAX_MAPLESTAR_LEVEL}）。\n"
            "輸入後會用官方經驗表作為升級時間與異常判斷基準。",
            initialvalue=current,
            parent=self.root,
        )
        if value is None:
            return
        level = self._valid_manual_level(value)
        if level is None:
            messagebox.showerror(
                "校正失敗",
                f"請輸入 {MIN_MAPLESTAR_LEVEL} 到 {MAX_MAPLESTAR_LEVEL} 之間的等級。",
            )
            return
        self._set_manual_level(level)
        if self._last_raw is not None and self._last_pct is not None:
            self._update_level_estimate(self._last_raw, self._last_pct)
        self.status.config(text=f"目前等級已校正為 Lv {level}，後續升級會自動遞增")
        messagebox.showinfo(
            "校正完成",
            f"目前等級已校正為 Lv {level}。\n"
            "這不會重置目前 EXP、累積 EXP、時間與效率。",
        )

    def _store_digit_templates(self, image, digits, boxes, trusted=False):
        key = "trusted_digit_templates" if trusted else "digit_templates"
        templates = self._settings.setdefault(key, {})
        added = 0
        for digit, box in zip(str(digits), boxes):
            template = _digit_template_from_box(image, box)
            if not template:
                continue
            bucket = templates.setdefault(digit, [])
            if template not in bucket:
                bucket.append(template)
                added += 1
            templates[digit] = bucket[-MAX_TEMPLATES_PER_DIGIT:]
        if added:
            self._save_settings()
            _set_digit_templates(
                self._settings.get("digit_templates", {}),
                self._settings.get("trusted_digit_templates", {}),
            )
        return added

    def _auto_learn_digit_templates(self, image, raw, pct):
        if raw is None or not _DIGIT_TEMPLATES:
            return 0
        digits = str(raw)
        boxes = _raw_digit_boxes(image, pct)
        if len(boxes) != len(digits):
            return 0

        for digit, box in zip(digits, boxes):
            learned_digit, confidence = _classify_digit_by_template(image, box)
            if learned_digit != digit or confidence < AUTO_LEARN_MIN_CONFIDENCE:
                return 0

        added = self._store_digit_templates(image, digits, boxes)
        self._learned_templates += added
        return added

    def start(self):
        if not self.window_obj or not self.exp_offset:
            return
        self.running = True
        if self.session_start is None:
            self.session_start = time.time()
        threading.Thread(target=self._loop, daemon=True).start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.compact_btn.config(state="normal")
        self.live_lbl.set("追蹤中", self.colors["accent_dark"], self.colors["fg"])
        self.status.config(text="追蹤中…請保持遊戲視窗未被遮住")
        self._tick_ui()

    def stop(self):
        self.running = False
        if self._compact_mode:
            self._show_full_window()
        self.start_btn.config(state="normal" if self.exp_offset else "disabled")
        self.stop_btn.config(state="disabled")
        self.compact_btn.config(state="disabled")
        self.live_lbl.set("待命", self.colors["panel_2"], self.colors["muted_text"])
        self.status.config(text="已停止")

    def reset(self):
        self.stop()
        self.samples.clear()
        self.total_gained = 0
        self._last_raw = None
        self._last_pct = None
        self._estimated_level = None
        self._level_estimate_error = None
        self._pending_raw = None
        self._pending_pct = None
        self._pending_at = None
        self._pending_jump_raw = None
        self._pending_jump_pct = None
        self._pending_jump_at = None
        self._manual_exp_floor_raw = None
        self._manual_exp_floor_level = None
        self._level_cap = None
        if self._manual_level is not None:
            self._estimated_level = self._manual_level
            self._level_estimate_error = 0.0
            self._level_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        self._ignored_samples = 0
        self._level_ups = 0
        self._learned_templates = 0
        self._capture_count = 0
        self._recognized_count = 0
        self._last_ocr_text = ""
        self._last_ocr_at = None
        self._last_error = ""
        self.session_start = None
        self.cur_lbl.config(text="目前 EXP：—")
        self.elapsed_lbl.config(text="00:00:00")
        self.gained_lbl.config(text="0")
        self.rate_lbl.config(text="—")
        self._refresh_level_label()
        self.ocr_lbl.config(text="尚未開始取樣")
        self.ocr_text_lbl.config(text="最後讀取：—")
        for w in (self.eta5, self.eta10, self.eta30, self.eta_level):
            w.config(text="—")
        if hasattr(self, "compact_rate_lbl"):
            self.compact_current_lbl.config(text="—")
            self.compact_rate_lbl.config(text="—")
            self.compact_eta5_lbl.config(text="—")
            self.compact_eta30_lbl.config(text="—")
            self.compact_level_lbl.config(text="—")

    def _apply_manual_exp_correction(self, raw, pct):
        now = time.time()
        previous_raw = self._last_raw
        previous_pct = self._last_pct
        adjustment = 0

        if previous_raw is not None:
            if is_level_reset(previous_raw, previous_pct, raw, pct):
                previous_cap = self._sample_level_cap(previous_raw, previous_pct) or self._level_cap
                if previous_cap and previous_cap >= previous_raw:
                    adjustment = max(0, int(round(previous_cap - previous_raw))) + raw
                    self._level_ups += 1
                    self._advance_manual_level()
            else:
                adjustment = raw - previous_raw

        if adjustment:
            self.total_gained = max(0, self.total_gained + adjustment)
            if self.samples and self.samples[-1][2] == previous_raw:
                self.samples.pop()

        self._last_raw = raw
        self._last_pct = pct
        self._pending_raw = None
        self._pending_pct = None
        self._pending_at = None
        self._clear_pending_jump()
        self._manual_exp_floor_raw = raw
        self._manual_exp_floor_level = self._manual_level or self._estimated_level
        self._update_level_estimate(raw, pct)

        self.samples.append((now, self.total_gained, raw, pct))
        cutoff = now - HISTORY_SECONDS
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()

        self.cur_lbl.config(text=f"目前 EXP：{raw:,}")
        self.gained_lbl.config(text=f"{self.total_gained:,}")
        self.level_lbl.config(text=self._level_display_text())
        if adjustment > 0:
            correction_text = f"手動校正：{raw:,}，累積 EXP 補上 {adjustment:,}"
        elif adjustment < 0:
            correction_text = f"手動校正：{raw:,}，累積 EXP 扣回 {abs(adjustment):,}"
        else:
            correction_text = f"手動校正：{raw:,}"
        self._last_ocr_text = correction_text
        self._last_ocr_at = now
        self._last_error = ""
        rate_text, eta5_text, eta10_text, eta30_text, level_eta_text = self._rate_display_values()
        self.rate_lbl.config(text=rate_text)
        self.eta5.config(text=eta5_text)
        self.eta10.config(text=eta10_text)
        self.eta30.config(text=eta30_text)
        self.eta_level.config(text=level_eta_text)
        self._update_compact_stats()

    def _overlay_threshold_pct(self, raw, pct):
        digit_count = None
        if self._last_raw is not None:
            digit_count = len(str(abs(int(self._last_raw))))
        elif raw is not None:
            digit_count = len(str(abs(int(raw))))
        if digit_count is None:
            return OCR_OVERLAP_BASE_PCT

        # Seven digits is the current tuning point. Longer EXP values place
        # the number further left, so the progress bar reaches it earlier.
        threshold = OCR_OVERLAP_BASE_PCT - max(0, digit_count - 7) * 4.0
        return max(OCR_OVERLAP_MIN_PCT, min(OCR_OVERLAP_BASE_PCT, threshold))

    def _dynamic_overlay_threshold_pct(self, image, raw, pct):
        threshold = self._overlay_threshold_pct(raw, pct)
        visual_count = visual_raw_digit_count(image, pct)
        if visual_count is not None:
            visual_threshold = OCR_OVERLAP_BASE_PCT - max(0, visual_count - 7) * 4.0
            threshold = min(threshold, visual_threshold)
        return max(OCR_OVERLAP_MIN_PCT, min(OCR_OVERLAP_BASE_PCT, threshold))

    def _sample_level_cap(self, raw, pct):
        if self._manual_level is not None:
            return float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        sample_estimate = self._sample_level_estimate(raw, pct)
        if sample_estimate:
            return float(sample_estimate[1])
        return level_cap_for_sample(raw, pct)

    def _expected_raw_from_pct(self, pct):
        if self._level_cap is None or pct is None or pct < 0:
            return None
        return self._level_cap * (pct / 100)

    def _reference_progress_pct(self, pct, visual_pct=None):
        pct_valid = pct is not None and 0 <= pct <= 100
        visual_valid = visual_pct is not None and 0 <= visual_pct <= 100
        if pct_valid:
            return pct
        if visual_valid:
            return visual_pct
        return None

    def _sample_level_estimate(self, raw, pct, visual_pct=None, max_error=LEVEL_SAMPLE_STRONG_MAX_ERROR):
        reference_pct = self._reference_progress_pct(pct, visual_pct)
        estimate = estimate_level_from_sample(raw, reference_pct)
        if estimate is None:
            return None
        if estimate[2] > max_error:
            return None
        return estimate

    def _progress_raw_tolerance(self):
        return max(
            MIN_DELTA_TOLERANCE,
            (self._level_cap or 0) * PROGRESS_RAW_TOLERANCE_RATIO,
        )

    def _raw_step_is_plausible(self, raw, pct, reference_cap=None):
        if raw is None or self._last_raw is None:
            return False
        if raw < self._last_raw:
            return is_level_reset(self._last_raw, self._last_pct, raw, pct)
        cap = reference_cap or self._level_cap
        if cap is not None and raw > cap * MAX_RAW_OVER_LEVEL_CAP_RATIO:
            return False
        delta = raw - self._last_raw
        if delta == 0:
            return True
        pct_delta = None
        if pct is not None and self._last_pct is not None:
            pct_delta = pct - self._last_pct
        expected_delta = expected_delta_from_percent(cap, pct_delta)
        tolerance = delta_tolerance(cap, expected_delta)
        if expected_delta is not None:
            return delta <= expected_delta + tolerance
        return delta <= max(MIN_DELTA_TOLERANCE * 4, (cap or raw) * 0.02)

    def _raw_is_plausible_for_progress(self, raw, pct, visual_pct=None):
        if raw is None:
            return False
        reference_pct = self._reference_progress_pct(pct, visual_pct)
        if self._manual_level is not None:
            manual_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
            if raw > manual_cap * MAX_RAW_OVER_LEVEL_CAP_RATIO:
                return False
            if self._raw_step_is_plausible(raw, pct, manual_cap):
                return True
            expected_raw = manual_cap * (reference_pct / 100) if reference_pct is not None else None
            if expected_raw is None:
                return True
            tolerance = max(MIN_DELTA_TOLERANCE, manual_cap * PROGRESS_RAW_TOLERANCE_RATIO)
            return abs(raw - expected_raw) <= tolerance
        sample_estimate = self._sample_level_estimate(raw, pct, visual_pct)
        if sample_estimate:
            level, _level_cap, _error = sample_estimate
            if self._manual_level is not None and abs(level - self._manual_level) > MAX_MANUAL_LEVEL_DRIFT:
                return False
            return True
        if self._level_cap is not None and raw > self._level_cap * MAX_RAW_OVER_LEVEL_CAP_RATIO:
            return False
        expected_raw = self._expected_raw_from_pct(reference_pct)
        if expected_raw is None:
            return True
        return abs(raw - expected_raw) <= self._progress_raw_tolerance()

    def _nearby_manual_level_for_sample(self, raw, pct, visual_pct=None):
        if self._manual_level is None or raw is None:
            return None
        reference_pct = self._reference_progress_pct(pct, visual_pct)
        if reference_pct is None or reference_pct <= 0:
            return None
        sample_cap = raw / (reference_pct / 100)
        start = self._manual_level
        end = min(MAX_MAPLESTAR_LEVEL, self._manual_level + MANUAL_LEVEL_AUTO_SYNC_LOOKAHEAD)
        best = None
        for level in range(start, end + 1):
            level_cap = MAPLESTAR_EXP_BY_LEVEL[level]
            error = abs(level_cap - sample_cap) / max(1, level_cap)
            if error <= MANUAL_LEVEL_AUTO_SYNC_MAX_ERROR:
                candidate = (error, level, level_cap)
                if best is None or candidate < best:
                    best = candidate
        return best

    def _sync_manual_level_from_sample(self, raw, pct, visual_pct=None):
        if self._manual_level is not None:
            return False
        estimate = self._sample_level_estimate(raw, pct, visual_pct)
        if estimate is None:
            return False
        level, level_cap, error = estimate
        if self._manual_level is not None and abs(level - self._manual_level) > MAX_MANUAL_LEVEL_DRIFT:
            return False
        if (
            self._last_raw is not None
            and self._last_pct is not None
            and raw is not None
            and pct is not None
            and raw > self._last_raw
        ):
            expected_delta = expected_delta_from_percent(level_cap, pct - self._last_pct)
            tolerance = delta_tolerance(level_cap, expected_delta)
            if expected_delta is not None and raw - self._last_raw > expected_delta + tolerance:
                return False
        if self._manual_level is None or level == self._manual_level:
            return False
        self._estimated_level = level
        self._level_estimate_error = error
        self._level_cap = float(level_cap)
        self._last_ocr_text = (
            f"{self._last_ocr_text}；EXP/% 較接近 Lv {level}，本次以讀值等級估算"
        )
        self.status.config(text=f"校正等級與讀值不一致，暫以 Lv {level} 估算")
        return True

    def _protect_unstable_overlay_raw(self, raw, pct, visual_pct=None, reason="讀值偏離進度"):
        if raw is None:
            return raw, pct
        if self._last_raw is None or self._level_cap is None:
            return raw, pct
        if self._raw_is_plausible_for_progress(raw, pct, visual_pct):
            return raw, pct
        reference_pct = self._reference_progress_pct(pct, visual_pct)
        expected_raw = self._expected_raw_from_pct(reference_pct)
        expected_text = f"，預期約 {int(round(expected_raw)):,}" if expected_raw is not None else ""
        self._ignored_samples += 1
        self.status.config(text="已忽略一次不可信 OCR：進度條覆蓋造成讀值偏離")
        self._last_ocr_text = (
            f"{self._last_ocr_text}；{reason}，忽略 {raw:,}{expected_text}，保留上一筆可信值 {self._last_raw:,}"
        )
        return self._last_raw, self._last_pct

    def _should_accept_backward_correction(self, previous_raw, previous_pct, raw, pct):
        if raw is None or previous_raw is None or raw >= previous_raw:
            return False
        if is_level_reset(previous_raw, previous_pct, raw, pct):
            return False
        if self._below_manual_exp_floor(raw, pct):
            return False

        tolerance = max(
            MIN_DELTA_TOLERANCE,
            (self._level_cap or 0) * BACKWARD_CORRECTION_CAP_RATIO,
        )
        expected_raw = self._expected_raw_from_pct(pct)
        if expected_raw is not None:
            previous_distance = abs(previous_raw - expected_raw)
            current_distance = abs(raw - expected_raw)
            if current_distance + tolerance < previous_distance:
                return True

        if len(self.samples) >= 2:
            _t, _gained, stable_raw, stable_pct = self.samples[-2]
            if stable_raw is not None and previous_raw > stable_raw and raw >= stable_raw:
                previous_jump = previous_raw - stable_raw
                corrected_step = raw - stable_raw
                expected_step = None
                if stable_pct is not None and pct is not None:
                    expected_step = expected_delta_from_percent(self._level_cap, pct - stable_pct)
                if expected_step is not None:
                    step_tolerance = delta_tolerance(self._level_cap, expected_step)
                    return abs(corrected_step - expected_step) <= step_tolerance and previous_jump > corrected_step + step_tolerance
                return previous_jump > max(MIN_DELTA_TOLERANCE, corrected_step * 3)

        return False

    def _accept_backward_correction(self, raw, pct, previous_raw):
        rollback = max(0, previous_raw - raw)
        if rollback:
            self.total_gained = max(0, self.total_gained - rollback)
            if self.samples and self.samples[-1][2] == previous_raw:
                self.samples.pop()
        self._ignored_samples += 1
        self.status.config(text=f"已修正一次 OCR 高讀，扣回多算 {rollback:,} EXP")
        self._last_ocr_text = f"{self._last_ocr_text}；修正高讀，改採 {raw:,}"

    def _clear_pending_jump(self):
        self._pending_jump_raw = None
        self._pending_jump_pct = None
        self._pending_jump_at = None

    def _below_manual_exp_floor(self, raw, pct):
        if self._manual_exp_floor_raw is None or raw is None:
            return False
        if raw >= self._manual_exp_floor_raw:
            return False
        if is_level_reset(self._manual_exp_floor_raw, self._last_pct, raw, pct):
            return False
        current_level = self._manual_level or self._estimated_level
        if (
            self._manual_exp_floor_level is not None
            and current_level is not None
            and current_level > self._manual_exp_floor_level
        ):
            return False
        return True

    def _rate_limit_from_positive_rates(self, positive_rates):
        if len(positive_rates) < RATE_OUTLIER_MIN_POSITIVE_SEGMENTS:
            return None
        rates = sorted(positive_rates)
        mid = len(rates) // 2
        if len(rates) % 2:
            median_rate = rates[mid]
        else:
            median_rate = (rates[mid - 1] + rates[mid]) / 2
        deviations = sorted(abs(rate - median_rate) for rate in rates)
        dev_mid = len(deviations) // 2
        if len(deviations) % 2:
            mad = deviations[dev_mid]
        else:
            mad = (deviations[dev_mid - 1] + deviations[dev_mid]) / 2
        return max(
            median_rate * RATE_OUTLIER_MULTIPLIER,
            median_rate + max(mad * RATE_OUTLIER_MAD_MULTIPLIER, MIN_DELTA_TOLERANCE * 60),
        )

    def _recent_positive_segment_rates(self, window_s=300):
        if len(self.samples) < 2:
            return []
        cutoff = self.samples[-1][0] - window_s
        rates = []
        for previous, current in zip(self.samples, list(self.samples)[1:]):
            if current[0] < cutoff:
                continue
            dt = current[0] - previous[0]
            gained = current[1] - previous[1]
            if dt > 0 and gained > 0:
                rates.append(gained / (dt / 60))
        return rates

    def _gain_delta_needs_confirmation(self, delta, elapsed_s, reference_cap=None):
        if delta <= 0 or elapsed_s <= 0:
            return False
        rate = delta / (elapsed_s / 60)
        recent_limit = self._rate_limit_from_positive_rates(self._recent_positive_segment_rates())
        if recent_limit is not None and rate > max(recent_limit, CUMULATIVE_JUMP_MIN_RATE):
            return True
        if reference_cap is not None:
            jump_limit = max(MIN_DELTA_TOLERANCE * 4, reference_cap * CUMULATIVE_JUMP_CONFIRM_RATIO)
            if delta > jump_limit and rate > CUMULATIVE_JUMP_MIN_RATE:
                return True
        return False

    def _pending_jump_confirmed(self, raw):
        if self._pending_jump_raw is None or raw is None:
            return False
        tolerance = max(MIN_DELTA_TOLERANCE, self._pending_jump_raw * 0.01)
        return raw >= self._pending_jump_raw - tolerance

    def _large_gain_matches_progress(self, raw, pct, visual_pct, delta, reference_cap=None):
        if raw is None or delta <= 0:
            return True
        cap = reference_cap or self._level_cap
        if cap is None:
            return True
        jump_limit = max(MIN_DELTA_TOLERANCE * 4, cap * CUMULATIVE_JUMP_CONFIRM_RATIO)
        if delta <= jump_limit:
            return True
        reference_pct = self._reference_progress_pct(visual_pct, pct)
        if reference_pct is None:
            return False
        expected_raw = cap * (reference_pct / 100)
        tolerance = max(MIN_DELTA_TOLERANCE, cap * PROGRESS_RAW_TOLERANCE_RATIO)
        return abs(raw - expected_raw) <= tolerance

    def _correct_8_to_9_by_context(self, raw, pct):
        if raw is None or pct is None or self._level_cap is None:
            return raw
        if self._sample_level_estimate(raw, pct):
            return raw
        digits = str(raw)
        if "8" not in digits:
            return raw

        expected_raw = self._expected_raw_from_pct(pct)
        if expected_raw is None:
            return raw

        current_distance = abs(raw - expected_raw)
        min_improvement = max(
            MIN_DELTA_TOLERANCE / 4,
            self._level_cap * CONFUSED_DIGIT_CORRECTION_RATIO,
        )
        candidates = []
        for idx, ch in enumerate(digits):
            if ch != "8":
                continue
            candidate = int(f"{digits[:idx]}9{digits[idx + 1:]}")
            if self._last_raw is not None and self._last_pct is not None:
                if pct >= self._last_pct and candidate < self._last_raw:
                    continue
                if pct < self._last_pct and not is_level_reset(self._last_raw, self._last_pct, candidate, pct):
                    continue
            candidate_distance = abs(candidate - expected_raw)
            improvement = current_distance - candidate_distance
            if improvement >= min_improvement:
                candidates.append((candidate_distance, -improvement, candidate, idx))

        if not candidates:
            return raw

        _distance, _improvement, corrected, idx = min(candidates)
        self._last_ocr_text = f"{self._last_ocr_text}；依等級與百分比將第 {idx + 1} 位 8 修正為 9：{corrected:,}"
        return corrected

    def _correct_8_to_9_by_previous_raw(self, raw, pct):
        if raw is None or self._last_raw is None:
            return raw
        if raw >= self._last_raw:
            return raw
        if is_level_reset(self._last_raw, self._last_pct, raw, pct):
            return raw

        digits = str(raw)
        if "8" not in digits:
            return raw

        reference_cap = self._level_cap
        if self._manual_level is not None:
            reference_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        max_step = max(MIN_DELTA_TOLERANCE * 4, (reference_cap or self._last_raw) * 0.025)
        candidates = []
        for idx, ch in enumerate(digits):
            if ch != "8":
                continue
            candidate = int(f"{digits[:idx]}9{digits[idx + 1:]}")
            if candidate < self._last_raw:
                continue
            if reference_cap is not None and candidate > reference_cap * MAX_RAW_OVER_LEVEL_CAP_RATIO:
                continue
            delta = candidate - self._last_raw
            if delta > max_step:
                continue
            candidates.append((delta, candidate, idx))

        if not candidates:
            return raw

        delta, corrected, idx = min(candidates, key=lambda item: item[0])
        self._last_ocr_text = (
            f"{self._last_ocr_text}；依上一筆可信 EXP 將第 {idx + 1} 位 8 修正為 9：{corrected:,}"
        )
        return corrected

    def _correct_pct_8_to_9_by_manual_level(self, raw, pct):
        if self._manual_level is None or raw is None or pct is None:
            return pct
        if not 80 <= pct < 90:
            return pct
        manual_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        pct_from_raw = raw / manual_cap * 100
        candidate_pct = pct + 10
        if candidate_pct > 100:
            return pct
        current_distance = abs(raw - manual_cap * (pct / 100))
        candidate_distance = abs(raw - manual_cap * (candidate_pct / 100))
        min_improvement = max(MIN_DELTA_TOLERANCE / 4, manual_cap * CONFUSED_DIGIT_CORRECTION_RATIO)
        if pct_from_raw >= 90 and current_distance - candidate_distance >= min_improvement:
            self._last_ocr_text = (
                f"{self._last_ocr_text}；依校正等級與 EXP 將百分比 {pct:.2f}% 修正為 {candidate_pct:.2f}%"
            )
            return candidate_pct
        return pct

    def _correct_pct_by_manual_level_and_step(self, raw, pct):
        if self._manual_level is None or raw is None:
            return pct
        manual_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        if manual_cap <= 0:
            return pct
        inferred_pct = raw / manual_cap * 100
        if inferred_pct < 0 or inferred_pct > 100:
            return pct
        if pct is not None and abs(pct - inferred_pct) < PCT_VISUAL_MISMATCH_TOLERANCE:
            return pct
        if self._last_raw is not None and not self._raw_step_is_plausible(raw, inferred_pct, manual_cap):
            return pct

        corrected_pct = round(inferred_pct, 2)
        if pct is None:
            self._last_ocr_text = (
                f"{self._last_ocr_text}；依校正等級與上一筆可信 EXP 補上百分比 {corrected_pct:.2f}%"
            )
        else:
            self._last_ocr_text = (
                f"{self._last_ocr_text}；依校正等級與上一筆可信 EXP 將百分比 {pct:.2f}% 修正為 {corrected_pct:.2f}%"
            )
        return corrected_pct

    def _correct_inserted_digit_by_level_cap(self, raw, pct):
        if raw is None or pct is None or self._level_cap is None:
            return raw
        raw_digits = str(raw)
        if len(raw_digits) < 2:
            return raw
        if self._last_raw is not None and len(raw_digits) <= len(str(self._last_raw)):
            return raw

        reference_level_cap = self._level_cap
        if self._manual_level is not None:
            reference_level_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        if pct > 0:
            expected_raw_for_level = reference_level_cap * (pct / 100)
            tolerance_for_level = max(MIN_DELTA_TOLERANCE, reference_level_cap * PROGRESS_RAW_TOLERANCE_RATIO)
            if abs(raw - expected_raw_for_level) <= tolerance_for_level:
                return raw

        original_cap = level_cap_for_sample(raw, pct)
        original_ratio = None
        if original_cap:
            smaller = max(1, min(original_cap, reference_level_cap))
            original_ratio = max(original_cap, reference_level_cap) / smaller

        expected_raw = None
        if self._last_raw is not None and self._last_pct is not None:
            pct_delta = pct - self._last_pct
            expected_delta = expected_delta_from_percent(reference_level_cap, pct_delta)
            if expected_delta is not None:
                expected_raw = self._last_raw + expected_delta
        if expected_raw is None:
            expected_raw = self._last_raw
        if expected_raw is None and pct is not None and pct > 0:
            expected_raw = reference_level_cap * (pct / 100)

        target_lengths = set()
        if self._last_raw is not None:
            last_len = len(str(self._last_raw))
            target_lengths.update({last_len - 1, last_len, last_len + 1})
        if reference_level_cap is not None and pct > 0:
            expected_raw_from_cap = int(round(reference_level_cap * (pct / 100)))
            cap_len = len(str(max(0, expected_raw_from_cap)))
            target_lengths.update({cap_len - 1, cap_len, cap_len + 1})
        target_lengths = {length for length in target_lengths if 2 <= length < len(raw_digits)}
        if not target_lengths:
            target_lengths.add(len(raw_digits) - 1)

        candidates = []
        pct_int_text = str(int(pct)) if pct is not None else ""
        pct_digits = f"{pct:.2f}".replace(".", "") if pct is not None else ""
        for target_len in sorted(target_lengths, reverse=True):
            remove_count = len(raw_digits) - target_len
            for remove_start in range(0, len(raw_digits) - remove_count + 1):
                candidate_digits = raw_digits[:remove_start] + raw_digits[remove_start + remove_count :]
                if not candidate_digits or candidate_digits.startswith("0"):
                    continue
                candidate = int(candidate_digits)
                if self._last_raw is not None and candidate < self._last_raw and (self._last_pct is None or pct >= self._last_pct):
                    continue
                candidate_cap = level_cap_for_sample(candidate, pct)
                if candidate_cap is None:
                    continue
                smaller = max(1, min(candidate_cap, reference_level_cap))
                ratio = max(candidate_cap, reference_level_cap) / smaller
                target_distance = abs(candidate - expected_raw) if expected_raw is not None else 0
                removed = raw_digits[remove_start : remove_start + remove_count]
                suffix_pollution = (
                    remove_start == target_len
                    and removed
                    and (
                        removed == pct_int_text
                        or removed == f"1{pct_int_text}"
                        or pct_digits.startswith(removed)
                        or pct_digits.startswith(removed.lstrip("1"))
                    )
                )
                candidates.append((0 if suffix_pollution else 1, ratio, target_distance, remove_count, candidate, removed))

        if not candidates:
            return raw

        acceptable = [item for item in candidates if item[1] <= BASELINE_CONFIRM_CAP_RATIO]
        pool = acceptable or candidates
        _suffix_rank, best_ratio, _distance, _remove_count, best_raw, removed = min(pool, key=lambda item: (item[2], item[0], item[1], item[3]))
        if best_ratio <= BASELINE_CONFIRM_CAP_RATIO and (original_ratio is None or best_ratio < original_ratio):
            self._last_ocr_text = (
                f"{self._last_ocr_text}；依等級基準移除疑似多讀位數 {removed}，修正為 {best_raw:,}"
            )
            return best_raw
        return raw

    def _correct_missing_prefix_by_manual_level_pct(self, raw, pct, visual_pct=None):
        if self._manual_level is None or raw is None:
            return raw
        reference_pct = self._reference_progress_pct(pct, visual_pct)
        if reference_pct is None or reference_pct <= 0 or reference_pct > 100:
            return raw

        manual_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
        expected_raw = manual_cap * (reference_pct / 100)
        tolerance = max(MIN_DELTA_TOLERANCE, manual_cap * PROGRESS_RAW_TOLERANCE_RATIO)
        if abs(raw - expected_raw) <= tolerance:
            return raw

        raw_digits = str(raw)
        expected_digits = str(max(0, int(round(expected_raw))))
        missing_count = len(expected_digits) - len(raw_digits)
        if missing_count <= 0 or missing_count > 3:
            return raw

        current_distance = abs(raw - expected_raw)
        min_prefix = 1 if missing_count == 1 else 10 ** (missing_count - 1)
        max_prefix = (10 ** missing_count) - 1
        candidates = []
        for prefix in range(min_prefix, max_prefix + 1):
            candidate = int(f"{prefix}{raw_digits}")
            if candidate > manual_cap * MAX_RAW_OVER_LEVEL_CAP_RATIO:
                continue
            if (
                self._last_raw is not None
                and candidate < self._last_raw
                and not is_level_reset(self._last_raw, self._last_pct, candidate, pct)
            ):
                continue
            distance = abs(candidate - expected_raw)
            if distance <= tolerance and current_distance - distance >= tolerance:
                candidates.append((distance, candidate, prefix))

        if not candidates:
            return raw

        _distance, corrected, prefix = min(candidates, key=lambda item: item[0])
        self._last_ocr_text = (
            f"{self._last_ocr_text}；依校正 Lv {self._manual_level} 與 {reference_pct:.2f}% 補回少讀前綴 {prefix}，修正為 {corrected:,}"
        )
        return corrected

    def _stabilize_overlay_sample(self, raw, pct, visual_pct, overlay_threshold=None):
        if raw is None:
            return raw, pct
        threshold = overlay_threshold if overlay_threshold is not None else self._overlay_threshold_pct(raw, pct)
        raw = self._correct_8_to_9_by_previous_raw(raw, pct)
        pct = self._correct_pct_8_to_9_by_manual_level(raw, pct)
        pct = self._correct_pct_by_manual_level_and_step(raw, pct)
        raw = self._correct_missing_prefix_by_manual_level_pct(raw, pct, visual_pct)
        raw = self._correct_inserted_digit_by_level_cap(raw, pct)
        self._sync_manual_level_from_sample(raw, pct, visual_pct)
        if self._level_cap is not None and self._last_raw is not None:
            raw, pct = self._protect_unstable_overlay_raw(raw, pct, visual_pct, reason="讀值偏離進度")
        if visual_pct is None or visual_pct < threshold:
            return raw, pct
        if self._level_cap is None or self._last_raw is None:
            return raw, pct

        sample_cap = level_cap_for_sample(raw, pct)
        suspicious = False
        if sample_cap is not None:
            smaller = max(1, min(sample_cap, self._level_cap))
            suspicious = max(sample_cap, self._level_cap) / smaller > BASELINE_CONFIRM_CAP_RATIO
        else:
            suspicious = raw < self._last_raw or len(str(raw)) != len(str(self._last_raw))
        if not suspicious:
            return raw, pct

        self._last_ocr_text = (
            f"{self._last_ocr_text}；進度條 {visual_pct:.1f}% 已達動態門檻 {threshold:.1f}%，保留上一筆可信值 {self._last_raw:,}"
        )
        return self._last_raw, self._last_pct

    def _loop(self):
        with mss.mss() as sct:
            while self.running:
                try:
                    win = self.window_obj
                    if win is None:
                        break
                    try:
                        wx, wy = int(win.left), int(win.top)
                    except Exception:
                        wx, wy = 0, 0
                    ox, oy, ow, oh = self.exp_offset
                    region = {"left": wx + ox, "top": wy + oy, "width": ow, "height": oh}
                    shot = sct.grab(region)
                    pil = Image.frombytes("RGB", shot.size, shot.rgb)
                    raw, pct, text = ocr_exp_detail(pil)
                    visual_pct = estimate_bar_percent(pil)
                    self._capture_count += 1
                    self._last_ocr_text = text
                    self._last_ocr_at = time.time()
                    self._last_error = ""
                    overlay_threshold = self._dynamic_overlay_threshold_pct(pil, raw, pct)
                    raw, pct = self._stabilize_overlay_sample(raw, pct, visual_pct, overlay_threshold)
                    if raw is not None:
                        if self._add_sample(time.time(), raw, pct, visual_pct):
                            self._recognized_count += 1
                except Exception as e:
                    self._last_error = str(e)
                    print(f"sample error: {e}", file=sys.stderr)
                wait_until = time.time() + float(self.sample_interval)
                while self.running and time.time() < wait_until:
                    time.sleep(min(0.1, wait_until - time.time()))

    def _add_sample(self, t, raw, pct, visual_pct=None):
        previous_raw = self._last_raw
        previous_pct = self._last_pct
        suspicious = False

        if raw is None:
            return False
        raw = self._correct_8_to_9_by_previous_raw(raw, pct)
        pct = self._correct_pct_8_to_9_by_manual_level(raw, pct)
        pct = self._correct_pct_by_manual_level_and_step(raw, pct)
        raw = self._correct_missing_prefix_by_manual_level_pct(raw, pct, visual_pct)
        raw = self._correct_inserted_digit_by_level_cap(raw, pct)
        raw = self._correct_8_to_9_by_context(raw, pct)
        self._sync_manual_level_from_sample(raw, pct, visual_pct)
        if self._below_manual_exp_floor(raw, pct):
            self._clear_pending_jump()
            self._ignored_samples += 1
            self.status.config(text="已忽略一次不可信 OCR：低於手動校正 EXP")
            self._last_ocr_text = (
                f"{self._last_ocr_text}；低於手動校正 EXP {self._manual_exp_floor_raw:,}，忽略 {raw:,}"
            )
            return False
        if not self._raw_is_plausible_for_progress(raw, pct, visual_pct):
            self._ignored_samples += 1
            self.status.config(text="已忽略一次不可信 OCR：讀值與進度條不一致")
            reference_pct = self._reference_progress_pct(pct, visual_pct)
            expected_raw = self._expected_raw_from_pct(reference_pct)
            expected_text = f"，預期約 {int(round(expected_raw)):,}" if expected_raw is not None else ""
            self._last_ocr_text = f"{self._last_ocr_text}；讀值與進度條不一致，忽略 {raw:,}{expected_text}"
            return False
        sample_cap = self._sample_level_cap(raw, pct)

        if previous_raw is None:
            if self._pending_raw is None:
                self._pending_raw = raw
                self._pending_pct = pct
                self._pending_at = t
                self.status.config(text="正在校準 EXP 讀值，等待下一次確認")
                return False

            pending_cap = self._sample_level_cap(self._pending_raw, self._pending_pct)
            confirmed = len(str(raw)) == len(str(self._pending_raw))
            if sample_cap and pending_cap:
                smaller = max(1, min(sample_cap, pending_cap))
                confirmed = confirmed and (max(sample_cap, pending_cap) / smaller <= BASELINE_CONFIRM_CAP_RATIO)
            else:
                confirmed = confirmed and abs(raw - self._pending_raw) <= max(
                    MIN_DELTA_TOLERANCE,
                    max(raw, self._pending_raw) * 0.25,
                )

            if not confirmed:
                self._pending_raw = raw
                self._pending_pct = pct
                self._pending_at = t
                self._ignored_samples += 1
                self.status.config(text="已忽略不穩定 EXP 讀值，重新校準中")
                return False

            self._pending_raw = None
            self._pending_pct = None
            self._pending_at = None
            self._last_raw = raw
            self._last_pct = pct
            self._update_level_estimate(raw, pct)
            self.samples.append((t, self.total_gained, raw, pct))
            return True

        if raw is not None and previous_raw is not None:
            delta = raw - previous_raw
            pct_delta = None
            if pct is not None and previous_pct is not None:
                pct_delta = pct - previous_pct

            cap_ratio = None
            if sample_cap and self._level_cap:
                smaller = max(1, min(sample_cap, self._level_cap))
                cap_ratio = max(sample_cap, self._level_cap) / smaller

            level_reset = is_level_reset(previous_raw, previous_pct, raw, pct)
            if cap_ratio is not None and cap_ratio > MAX_LEVEL_CAP_RATIO_JUMP:
                if sample_cap < self._level_cap and not level_reset:
                    self._ignored_samples += 1
                    self.status.config(text="已忽略一次不可信 OCR：經驗值少讀")
                    return False

            # OCR occasionally drops or adds a digit. Compare the raw EXP delta
            # with the delta implied by the percentage, so the rule scales from
            # millions to billions instead of using a fixed EXP cap.
            reference_cap = self._level_cap or self._sample_level_cap(previous_raw, previous_pct)
            expected_delta = expected_delta_from_percent(reference_cap, pct_delta)
            tolerance = delta_tolerance(reference_cap, expected_delta)
            suspicious_jump = (
                delta > 0
                and expected_delta is not None
                and delta > expected_delta + tolerance
            )
            suspicious_flat_pct = delta > 0 and pct_delta is not None and pct_delta <= 0.01 and delta > MIN_DELTA_TOLERANCE
            suspicious_cap = cap_ratio is not None and cap_ratio > MAX_LEVEL_CAP_RATIO_JUMP
            suspicious_pct = delta > 0 and pct_delta is not None and pct_delta < 0
            suspicious = suspicious_jump or suspicious_flat_pct or suspicious_cap or suspicious_pct

            if delta > 0 and not suspicious:
                elapsed_s = max(float(self.sample_interval), t - self.samples[-1][0]) if self.samples else float(self.sample_interval)
                if not self._large_gain_matches_progress(raw, pct, visual_pct, delta, reference_cap):
                    self._clear_pending_jump()
                    self._ignored_samples += 1
                    reference_pct = self._reference_progress_pct(visual_pct, pct)
                    expected_raw = reference_cap * (reference_pct / 100) if reference_cap and reference_pct is not None else None
                    expected_text = f"，進度預期約 {int(round(expected_raw)):,}" if expected_raw is not None else ""
                    self.status.config(text="已忽略一次不可信 OCR：跳高讀值與進度不一致")
                    self._last_ocr_text = (
                        f"{self._last_ocr_text}；累積保護：忽略跳高 +{delta:,} EXP{expected_text}"
                    )
                    return False
                confirmed_pending_jump = self._pending_jump_confirmed(raw)
                if (
                    not confirmed_pending_jump
                    and self._gain_delta_needs_confirmation(delta, elapsed_s, reference_cap)
                ):
                    self._pending_jump_raw = raw
                    self._pending_jump_pct = pct
                    self._pending_jump_at = t
                    self._ignored_samples += 1
                    self.status.config(text="已暫停一次過大的 EXP 跳動，等待下一次取樣確認")
                    self._last_ocr_text = (
                        f"{self._last_ocr_text}；累積保護：暫不加入跳動 +{delta:,} EXP，等待下一筆確認"
                    )
                    return False
                self._clear_pending_jump()
                self.total_gained += delta
            elif delta > 0:
                self._clear_pending_jump()
                self._ignored_samples += 1
                self.status.config(text="已忽略一次異常跳動，並重新校準 EXP 基準")
                return False
            elif level_reset:
                self._clear_pending_jump()
                previous_cap = self._sample_level_cap(previous_raw, previous_pct) or self._level_cap
                if previous_cap and previous_cap >= previous_raw:
                    remaining = max(0, int(round(previous_cap - previous_raw)))
                    self.total_gained += remaining + raw
                    self._level_ups += 1
                    self._advance_manual_level()
                    self.status.config(
                        text=f"偵測到升級，已補算升級前剩餘 {remaining:,} EXP"
                    )
                else:
                    self._ignored_samples += 1
                    self.status.config(text="偵測到 EXP 歸零，但缺少可靠基準，已重新校準")
                    return False
            elif delta < 0:
                self._clear_pending_jump()
                self._ignored_samples += 1
                self.status.config(text="已忽略一次不可信 OCR：經驗值回退")
                self._last_ocr_text = (
                    f"{self._last_ocr_text}；同一等級 EXP 不應低於上一筆可信值 {previous_raw:,}，忽略 {raw:,}"
                )
                return False

        if raw is not None:
            self._last_raw = raw
        if pct is not None:
            self._last_pct = pct
        if sample_cap is not None:
            self._update_level_estimate(raw, pct)
            if self._level_cap is None or suspicious:
                self._level_cap = sample_cap
            elif raw is not None and previous_raw is not None and raw >= previous_raw:
                self._level_cap = self._level_cap * 0.8 + sample_cap * 0.2
            else:
                self._level_cap = sample_cap
        self.samples.append((t, self.total_gained, raw, pct))
        cutoff = t - HISTORY_SECONDS
        while self.samples and self.samples[0][0] < cutoff:
            self.samples.popleft()
        return True

    def _rate_per_min(self, window_s: float):
        if len(self.samples) < 2:
            return None
        now = self.samples[-1][0]
        cutoff = now - window_s
        window_samples = []
        previous = None
        for sample in self.samples:
            if sample[0] < cutoff:
                previous = sample
                continue
            if previous is not None and not window_samples:
                window_samples.append(previous)
            window_samples.append(sample)
        if len(window_samples) < 2:
            return None

        span = window_samples[-1][0] - window_samples[0][0]
        if span < 20:
            return None

        segments = []
        for previous, current in zip(window_samples, window_samples[1:]):
            dt = current[0] - previous[0]
            gained = current[1] - previous[1]
            if dt <= 0 or gained < 0:
                continue
            segments.append((dt, gained, gained / (dt / 60)))

        if not segments:
            return 0

        filtered = segments
        positive_rates = sorted(rate for _dt, gained, rate in segments if gained > 0)
        if len(positive_rates) >= RATE_OUTLIER_MIN_POSITIVE_SEGMENTS:
            mid = len(positive_rates) // 2
            if len(positive_rates) % 2:
                median_rate = positive_rates[mid]
            else:
                median_rate = (positive_rates[mid - 1] + positive_rates[mid]) / 2
            deviations = sorted(abs(rate - median_rate) for rate in positive_rates)
            dev_mid = len(deviations) // 2
            if len(deviations) % 2:
                mad = deviations[dev_mid]
            else:
                mad = (deviations[dev_mid - 1] + deviations[dev_mid]) / 2
            outlier_limit = max(
                median_rate * RATE_OUTLIER_MULTIPLIER,
                median_rate + max(mad * RATE_OUTLIER_MAD_MULTIPLIER, MIN_DELTA_TOLERANCE * 60),
            )
            filtered = [
                (dt, gained, rate)
                for dt, gained, rate in segments
                if gained == 0 or rate <= outlier_limit
            ]

        trusted_gained = sum(gained for _dt, gained, _rate in filtered)
        return trusted_gained / (span / 60)

    def _format_eta_duration(self, seconds):
        if seconds < 60:
            return "小於 1 分鐘"
        minutes = max(1, int(round(seconds / 60)))
        days, rem = divmod(minutes, 1440)
        hours, mins = divmod(rem, 60)
        if days:
            return f"{days}天 {hours:02}:{mins:02}"
        if hours:
            return f"{hours}小時 {mins}分"
        return f"{mins}分鐘"

    def _update_level_estimate(self, raw, pct):
        if self._manual_level is not None:
            manual_cap = float(MAPLESTAR_EXP_BY_LEVEL[self._manual_level])
            self._estimated_level = self._manual_level
            self._level_estimate_error = 0.0
            self._level_cap = manual_cap
            return manual_cap
        estimate = estimate_level_from_sample(raw, pct)
        if estimate:
            self._estimated_level, level_cap, self._level_estimate_error = estimate
            self._level_cap = float(level_cap)
            return float(level_cap)
        self._estimated_level = None
        self._level_estimate_error = None
        return level_cap_from_sample(raw, pct)

    def _level_display_text(self):
        if self._manual_level is not None:
            return f"Lv {self._manual_level}（校正）"
        if self._estimated_level is None:
            return "—"
        return f"Lv {self._estimated_level}"

    def _level_eta_text(self, rate=None):
        if not self.samples or self._last_raw is None:
            return "—"
        if self._last_pct is None:
            return "尚未讀到 %"
        if rate is None:
            rate = self._rate_per_min(window_s=300)
        if rate is None or rate <= 0:
            return "等待速率"

        level_cap = self._level_cap or level_cap_for_sample(self._last_raw, self._last_pct)
        if level_cap is None:
            return "建立基準中"
        remaining = max(0, level_cap - self._last_raw)
        if remaining <= 0:
            return "即將升級"

        seconds = remaining / rate * 60
        eta_at = time.strftime("%H:%M", time.localtime(time.time() + seconds))
        return f"{self._format_eta_duration(seconds)}（{eta_at}）"

    def _rate_display_values(self):
        rate = self._rate_per_min(window_s=300)
        level_eta = self._level_eta_text(rate)
        if rate is not None and rate > 0:
            return f"{rate:,.0f} / 分", f"{rate*5:,.0f}", f"{rate*10:,.0f}", f"{rate*30:,.0f}", level_eta
        if self._recognized_count == 0:
            return "尚未讀到 EXP", "—", "—", "—", "—"
        if len(self.samples) < 2:
            return "等待第二筆樣本", "—", "—", "—", level_eta
        if self._last_raw is None:
            return "只讀到百分比", "—", "—", "—", "—"
        if rate == 0:
            return "未偵測到增加", "—", "—", "—", "等待速率"
        return "建立基準中", "—", "—", "—", level_eta

    def _update_compact_stats(self):
        if not hasattr(self, "compact_rate_lbl"):
            return
        rate_text, eta5_text, _eta10_text, eta30_text, level_eta_text = self._rate_display_values()
        current_text = "—"
        if self.samples:
            _t, _gained, raw, pct = self.samples[-1]
            current_text = exp_display_grouped(raw, pct)
        self.compact_current_lbl.config(text=current_text)
        self.compact_rate_lbl.config(text=rate_text)
        self.compact_eta5_lbl.config(text=eta5_text)
        self.compact_eta30_lbl.config(text=eta30_text)
        self.compact_level_lbl.config(text=level_eta_text)

    def _tick_ui(self):
        if self.samples:
            _, _, raw, pct = self.samples[-1]
            self.cur_lbl.config(text=f"目前 EXP：{exp_display_grouped(raw, pct)}")

        if self.session_start:
            elapsed = time.time() - self.session_start
            hh, rem = divmod(int(elapsed), 3600)
            mm, ss = divmod(rem, 60)
            self.elapsed_lbl.config(text=f"{hh:02}:{mm:02}:{ss:02}")
            self.gained_lbl.config(text=f"{self.total_gained:,}")

            rate_text, eta5_text, eta10_text, eta30_text, level_eta_text = self._rate_display_values()
            self.rate_lbl.config(text=rate_text)
            self.level_lbl.config(text=self._level_display_text())
            self.eta5.config(text=eta5_text)
            self.eta10.config(text=eta10_text)
            self.eta30.config(text=eta30_text)
            self.eta_level.config(text=level_eta_text)
            self._update_compact_stats()

        self._update_ocr_status()

        if self.running:
            self.root.after(500, self._tick_ui)

    def _update_ocr_status(self):
        self.ocr_device_lbl.config(text=ocr_device_status())
        parts = [f"截圖 {self._capture_count} 次", f"成功辨識 {self._recognized_count} 次"]
        if self._level_ups:
            parts.append(f"升級 {self._level_ups} 次")
        if self._manual_level is not None:
            parts.append(f"校正 Lv {self._manual_level}")
        elif self._estimated_level is not None:
            parts.append(f"推估 Lv {self._estimated_level}")
        if self._ignored_samples:
            parts.append(f"已忽略異常 {self._ignored_samples} 次")
        if self._last_error:
            parts.append(f"錯誤：{self._last_error}")
        elif self._last_ocr_at:
            ago = max(0, int(time.time() - self._last_ocr_at))
            parts.append(f"上次取樣 {ago} 秒前")
        diag_width = max(260, self.ocr_text_lbl.winfo_width() - 16)
        self.ocr_lbl.config(text=" / ".join(parts), wraplength=diag_width)

        text = " ".join((self._last_ocr_text or "").split())
        if not text:
            text = "—"
        self.ocr_text_lbl.config(text=f"最後讀取：{text}", wraplength=diag_width)


def main():
    if "--self-test-ocr" in sys.argv:
        engine = _pp_ocr_engine()
        if engine is not None:
            sys.exit(0)
        try:
            app_data_dir().mkdir(parents=True, exist_ok=True)
            (app_data_dir() / "self_test_ocr_error.txt").write_text(
                (_PP_OCR_ERROR or "PP-OCRv5 初始化失敗") + "\n\n" + traceback.format_exc(),
                encoding="utf-8",
            )
        except Exception:
            pass
        sys.exit(1)

    if pwc is None:
        print("缺少套件 pywinctl，請執行：pip install pywinctl", file=sys.stderr)
        try:
            r = tk.Tk(); r.withdraw()
            messagebox.showerror("缺少套件", "未安裝 pywinctl，請先執行：\npip install pywinctl")
        except Exception:
            pass
        sys.exit(1)

    ocr_available = PaddleOCR is not None and np is not None
    if not ocr_available:
        msg = (
            "找不到可用的 OCR 引擎。\n\n"
            "請確認此 exe 檔案完整。\n"
            "若仍無法啟動，請回報錯誤內容。\n\n"
            f"{_PP_OCR_IMPORT_ERROR or ''}"
        )
        print(msg, file=sys.stderr)
        try:
            r = tk.Tk(); r.withdraw()
            messagebox.showerror("找不到 OCR 引擎", msg)
        except Exception:
            pass
        sys.exit(1)

    root = tk.Tk()
    ExpTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()

