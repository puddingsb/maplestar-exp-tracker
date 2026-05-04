# MapleStar EXP Tracker

Tkinter desktop app for tracking MapleStory EXP by capturing a selected game-window region and reading the EXP text with PP-OCRv5 + PaddleOCR.

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
python exp_tracker.py
```

PP-OCRv5 + PaddleOCR CPU is the only OCR engine used by the app.

## Build Windows EXE

Run this on Windows:

```powershell
.\scripts\build_windows.ps1
```

Output:

```text
dist\MapleStar-EXP-Tracker.exe
```

Verify the packaged app can initialize PP-OCRv5:

```powershell
$p = Start-Process .\dist\MapleStar-EXP-Tracker.exe -ArgumentList "--self-test-ocr" -Wait -PassThru
$p.ExitCode
```

`0` means PP-OCRv5 initialized successfully.

## Build macOS App and DMG

Run this on macOS:

```bash
chmod +x scripts/build_macos_dmg.sh
./scripts/build_macos_dmg.sh
```

Outputs:

```text
dist/MapleStar-EXP-Tracker.app
dist/MapleStar-EXP-Tracker.dmg
```

macOS users may need to grant Screen Recording and Accessibility permissions to the app.

## Notes

Build the Windows `.exe` on Windows and the macOS `.dmg` on macOS. PyInstaller does not reliably cross-compile these desktop bundles from the other operating system.
