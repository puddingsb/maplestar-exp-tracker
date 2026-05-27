# Packaging Guide

## Scope

This file applies to `packaging/`.

## Responsibilities

- Keep PyInstaller specs and platform metadata here.
- Preserve release compatibility for existing executable names unless a versioned migration is intentional.
- Update packaging files when imports move into new modules.

## Verification

- For Windows packaging changes, run `scripts/build_windows.ps1` before release.
- For macOS packaging changes, run `scripts/build_macos_dmg.sh` on macOS before release.
