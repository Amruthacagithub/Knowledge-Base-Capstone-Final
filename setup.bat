@echo off
REM First-time setup — double-click this (Windows)
cd /d "%~dp0"
echo.
echo Starting Trust-RAG setup (needs Docker Desktop running)...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_local.ps1"
if errorlevel 1 (
  echo.
  echo SETUP FAILED. Fix the error above and try again.
  pause
  exit /b 1
)
echo.
pause
