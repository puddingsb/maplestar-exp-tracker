$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$ThreadCount = [Math]::Max(2, [Environment]::ProcessorCount)
$env:CMAKE_BUILD_PARALLEL_LEVEL = "$ThreadCount"
$env:MAKEFLAGS = "-j$ThreadCount"
Write-Host "Build thread settings: $ThreadCount threads"

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    python -m venv .venv
}

& $VenvPython -m pip install --upgrade pip
$GpuPackages = @(
    "meikiocr",
    "rapidocr",
    "rapidocr-onnxruntime",
    "opencv-python",
    "opencv-python-headless",
    "onnxruntime",
    "paddlepaddle-gpu",
    "nvidia-cublas-cu12",
    "nvidia-cuda-runtime-cu12",
    "nvidia-cudnn-cu12",
    "nvidia-cufft-cu12",
    "nvidia-curand-cu12",
    "nvidia-cusolver-cu12",
    "nvidia-cusparse-cu12",
    "nvidia-nvjitlink-cu12"
)
& $VenvPython -m pip uninstall -y @GpuPackages
& $VenvPython -m pip install -r requirements.txt -r requirements-build.txt
Write-Host "PP-OCRv5 + PaddleOCR CPU is the only OCR engine used by this build."
Write-Host "Preparing bundled PP-OCRv5 models..."
& $VenvPython exp_tracker.py --self-test-ocr

& $VenvPython -m PyInstaller --clean --noconfirm packaging\windows-onefile.spec

Write-Host ""
Write-Host "Built Windows executable:"
Write-Host "  $Root\dist\MapleStar-EXP-Tracker.exe"
