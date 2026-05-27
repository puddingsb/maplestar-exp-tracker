# Tracker Module Guide

## Scope

This file applies to `tracker/`.

## Responsibilities

- Put reusable non-UI logic here: rate calculations, OCR helpers, parsing, correction, settings, capture, and tracker state machines.
- Modules should avoid importing `exp_tracker.py`. Pass callbacks or data into tracker modules instead of creating circular imports.
- Keep module APIs small and explicit so `exp_tracker.py` can remain the app shell.

## Style

- Prefer pure functions and small classes with minimal Tkinter dependencies.
- Do not access global app settings directly from these modules unless the module is specifically about settings.
