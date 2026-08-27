@echo off
REM Everyday start — double-click this (Windows)
cd /d "%~dp0"
echo.
echo Starting Trust-RAG...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local.ps1"
if errorlevel 1 (
  echo.
  echo START FAILED. Did you run setup.bat first? Is Docker Desktop running?
  pause
  exit /b 1
)
echo.
pause
