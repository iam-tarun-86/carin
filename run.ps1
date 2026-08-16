# Zero-Latency Native Windows Voice Agent Launcher

param (
    [string]$ModelPath = "",
    [int]$Port = 8085
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "      ZERO-LATENCY NATIVE WINDOWS VOICE AGENT LAUNCHER      " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if llama.cpp server is active on port 8085
$serverReady = $false
try {
    $res = Invoke-WebRequest -Uri "http://localhost:$Port/v1/models" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($res.StatusCode -eq 200) {
        $serverReady = $true
    }
} catch {
    $serverReady = $false
}

if (-not $serverReady) {
    Write-Host "[INFO] llama.cpp server is NOT currently running on port $Port." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please start llama-server inside your WSL 2 terminal:" -ForegroundColor Yellow
    Write-Host "   ./llama-server -m /path/to/your/model.gguf --host 0.0.0.0 --port $Port -ngl 99 -c 2048" -ForegroundColor Green
    Write-Host ""
    
    $answer = Read-Host "Would you like to start the voice agent orchestrator anyway? (y/n)"
    if ($answer.ToLower() -ne 'y') {
        exit
    }
} else {
    Write-Host "[SUCCESS] Connected to llama.cpp server on port $Port!" -ForegroundColor Green
}

Write-Host ""
Write-Host "[INFO] Starting Voice Agent Orchestrator & React UI Dev Server..." -ForegroundColor Cyan
Write-Host ""

# Function to clean up processes by port and PID tree
function Stop-VoiceAgentProcesses {
    param([int]$VitePid, [int]$TTSPid)
    Write-Host ""
    Write-Host "[INFO] Cleaning up background servers..." -ForegroundColor Cyan

    if ($VitePid) {
        taskkill.exe /F /T /PID $VitePid 2>$null
    }
    if ($TTSPid) {
        taskkill.exe /F /T /PID $TTSPid 2>$null
    }

    # Clean up any leftover listeners on ports 8086, 5173, 8765
    $ports = @(8086, 5173, 8765)
    foreach ($p in $ports) {
        $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
        if ($conns) {
            foreach ($c in $conns) {
                if ($c.OwningProcess -and $c.OwningProcess -gt 0) {
                    taskkill.exe /F /T /PID $c.OwningProcess 2>$null
                }
            }
        }
    }
}

# Pre-cleanup in case previous instances are still running
Stop-VoiceAgentProcesses -VitePid 0 -TTSPid 0

# Suppress noisy library warnings
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:HF_HUB_DISABLE_IMPLICIT_TOKEN = "1"
$env:TOKENIZERS_PARALLELISM = "false"
$env:PYTHONWARNINGS = "ignore"

# Start Pocket TTS Server in background with INT8 quantization (logging to background log)
Write-Host "[INFO] Starting Pocket TTS Server on port 8086 (Quantized)..." -ForegroundColor Cyan
$ttsLog = Join-Path $env:TEMP "pocket_tts.log"
$PocketTTSProcess = Start-Process cmd.exe -ArgumentList "/c .\venv311\Scripts\pocket-tts.exe serve --port 8086 --quantize > `"$ttsLog`" 2>&1" -NoNewWindow -PassThru

# Start React Dev Server in background
Write-Host "[INFO] Starting React UI Dev Server..." -ForegroundColor Cyan
$ViteProcess = Start-Process cmd.exe -ArgumentList "/c npm run dev --prefix ui-react" -NoNewWindow -PassThru

try {
    Write-Host "[INFO] Starting Voice Agent Orchestrator (main.py)..." -ForegroundColor Cyan
    & ".\venv311\Scripts\python.exe" "main.py"
} finally {
    $vPid = if ($ViteProcess) { $ViteProcess.Id } else { 0 }
    $tPid = if ($PocketTTSProcess) { $PocketTTSProcess.Id } else { 0 }
    Stop-VoiceAgentProcesses -VitePid $vPid -TTSPid $tPid
    Write-Host "[INFO] All services stopped cleanly." -ForegroundColor Green
}
