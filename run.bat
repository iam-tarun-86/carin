@echo off
title Carin - Zero-Latency Native Voice Agent
setlocal

:: Ensure working directory is the script directory
cd /d "%~dp0"

:: Delegate execution to run.ps1 with ExecutionPolicy Bypass
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [INFO] Application exited with code %ERRORLEVEL%.
    pause
)

endlocal
