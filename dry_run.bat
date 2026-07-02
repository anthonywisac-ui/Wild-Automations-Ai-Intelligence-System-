@echo off
REM Dry-run test: validate config, crawl sample portals, skip delivery
REM Usage: dry_run.bat

setlocal enabledelayedexpansion

echo === Wild Automations Dry-Run Test ===
echo.
echo This will:
echo   1. Load and validate bot manifest
echo   2. Attempt to crawl configured portals
echo   3. Print per-portal stats
echo   4. Skip AI processing and delivery
echo.

REM Check .env exists
if not exist ".env" (
    echo ERROR: .env not found
    echo Copy .env.example to .env and fill in your values
    exit /b 1
)

echo Starting dry-run...
echo.

setlocal
for /f "delims== tokens=1,2" %%a in (.env) do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
)
endlocal & (
    set DRY_RUN=true
    python main.py
)

echo.
echo === Dry-Run Complete ===
echo Check output above for per-portal stats and any validation errors.
echo.
echo If all portals crawled successfully (0 items expected since selectors are placeholders),
echo the system is ready for:
echo   1. Real portal config with verified selectors
echo   2. Live database credentials
echo   3. Production deployment
