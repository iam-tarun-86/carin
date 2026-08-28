@echo off
title Carin - Zero-Latency Native Voice Agent
setlocal

:: Ensure working directory is the script directory
cd /d "%~dp0"

:: Delegate execution to run.ps1 with ExecutionPolicy Bypass
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*

endlocal
