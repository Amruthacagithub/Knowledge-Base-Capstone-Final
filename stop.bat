@echo off
REM Stop the app — double-click this (Windows)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_local.ps1"
pause
