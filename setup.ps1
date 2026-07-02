# Wild Automations - Production Setup (Windows PowerShell)
# Usage: .\setup.ps1

param(
    [switch]$SkipBrowsers = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=== Wild Automations Setup ===" -ForegroundColor Cyan

# 1. Check Python
Write-Host "`n[1/4] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if (-not $?) {
    Write-Host "ERROR: Python not found or not in PATH" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# 2. Create venv (optional but recommended)
Write-Host "`n[2/4] Virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    Write-Host "Creating venv..." -ForegroundColor Cyan
    python -m venv venv
    Write-Host "Created. Activate with: .\venv\Scripts\Activate.ps1" -ForegroundColor Green
} else {
    Write-Host "venv already exists" -ForegroundColor Green
}

# 3. Install pip packages
Write-Host "`n[3/4] Installing pip packages..." -ForegroundColor Yellow
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

if (-not $?) {
    Write-Host "ERROR: pip install failed" -ForegroundColor Red
    exit 1
}
Write-Host "Pip packages installed" -ForegroundColor Green

# 4. Install Playwright browsers
if ($SkipBrowsers) {
    Write-Host "`n[4/4] Skipping browser install (--SkipBrowsers)" -ForegroundColor Yellow
} else {
    Write-Host "`n[4/4] Installing Playwright browsers..." -ForegroundColor Yellow
    playwright install chromium
    if (-not $?) {
        Write-Host "ERROR: playwright install failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "Playwright browsers installed" -ForegroundColor Green
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Activate venv: .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  2. Set env vars: copy .env.example .env && edit .env" -ForegroundColor White
Write-Host "  3. Dry run: python main.py (with DRY_RUN=true)" -ForegroundColor White
