# MapleStar EXP Tracker Repository Guide

## Scope

This file applies to the whole repository unless a nested `AGENTS.md` overrides it.

## Project Shape

- `exp_tracker.py` is still the application entry point and legacy integration layer.
- New code should move toward small modules under `tracker/` instead of adding more large blocks to `exp_tracker.py`.
- Keep OCR correction behavior conservative. A UI refactor should not change EXP adoption, upgrade detection, or accumulated EXP semantics unless that is the explicit task.

## Editing Rules

- Prefer extracting pure helpers first, then wiring them from `exp_tracker.py`.
- Keep Windows packaging paths and app-data paths compatible with existing releases.
- Do not commit generated OCR experiment images, virtual environments, build output, or `dist/` output.
- After every code or packaging change, bump the app version in `exp_tracker.py` and matching packaging metadata, then produce a fresh build unless the user explicitly says to skip building.

## Verification

- Run `python -m py_compile exp_tracker.py tracker/*.py` after code changes.
- Run `python exp_tracker.py --self-test-ocr` when OCR initialization or packaging paths change.
- Run `scripts/build_windows.ps1` after versioned Windows changes.
