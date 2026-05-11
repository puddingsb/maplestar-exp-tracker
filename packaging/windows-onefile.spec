# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata


project_root = Path(SPECPATH).parent
datas = []
binaries = []
paddlex_models = [
    "PP-OCRv5_mobile_det",
    "en_PP-OCRv5_mobile_rec",
]

def add_data_tree(source, dest):
    source = Path(source)
    if not source.exists():
        return
    for path in source.rglob("*"):
        if path.is_file():
            rel_parent = path.relative_to(source).parent
            datas.append((str(path), str(Path(dest) / rel_parent)))

for model_name in paddlex_models:
    add_data_tree(Path.home() / ".paddlex" / "official_models" / model_name, Path("paddlex_models") / model_name)

add_data_tree(project_root / "assets", "assets")

datas += collect_data_files("paddleocr")
datas += collect_data_files("paddlex")
datas += copy_metadata("paddleocr")
datas += copy_metadata("paddlex")
datas += copy_metadata("paddlepaddle")
datas += copy_metadata("opencv-contrib-python")
for dist_name in [
    "imagesize",
    "pyclipper",
    "pypdfium2",
    "python-bidi",
    "shapely",
]:
    datas += copy_metadata(dist_name)

binaries += collect_dynamic_libs("paddle")
hiddenimports = []
hiddenimports += collect_submodules("pywinctl")
hiddenimports += collect_submodules("paddleocr")
hiddenimports += [
    "paddle",
    "paddlex",
    "cv2",
    "imagesize",
    "pyclipper",
    "pypdfium2",
    "bidi",
    "shapely",
]

a = Analysis(
    [str(project_root / "exp_tracker.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "meikiocr",
        "rapidocr",
        "torch",
        "tensorflow",
        "tensorflow_core",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MapleStar-EXP-Tracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "app_icon.ico"),
    version=str(project_root / "packaging" / "windows-version-info.txt"),
)
