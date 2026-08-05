@echo off
title Zero-Latency Native Windows Voice Agent

echo ============================================================
echo       ZERO-LATENCY NATIVE WINDOWS VOICE AGENT
echo ============================================================
echo.

:: 1. Check if virtual environment exists
if not exist ".\venv311\Scripts\python.exe" (
    echo [ERROR] Python 3.11 environment not found at .\venv311\Scripts\python.exe
    echo Please ensure the project environment is set up.
    pause
    exit /b 1
)

:: 2. Check WSL 2 LLM Server readiness
echo [1/2] Checking connection to llama.cpp server on WSL 2 (http://localhost:8085)...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8085/v1/models' -TimeoutSec 3; Write-Host '[SUCCESS] Connected to llama.cpp server!' } catch { Write-Host '[WARNING] Could not reach llama.cpp server on port 8085.' -ForegroundColor Yellow; Write-Host '          Make sure llama-server is running in WSL 2 with: ./llama-server -m <model.gguf> --host 0.0.0.0 --port 8085' -ForegroundColor Yellow }"

echo.
echo [2/2] Launching Voice Agent Orchestrator...
echo.

:: 3. Launch main voice agent pipeline
.\venv311\Scripts\python.exe main.py

pause
