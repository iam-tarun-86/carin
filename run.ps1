# Zero-Latency Native Windows Voice Agent Launcher
param (
    [string]$ModelPath = "",
    [int]$Port = 8085
)

$Host.UI.RawUI.WindowTitle = "Carin - Native Voice Agent"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "      ZERO-LATENCY NATIVE WINDOWS VOICE AGENT LAUNCHER      " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Suppress noisy library warnings globally
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:HF_HUB_DISABLE_IMPLICIT_TOKEN = "1"
$env:TOKENIZERS_PARALLELISM = "false"
$env:PYTHONWARNINGS = "ignore"

# 2. Function to thoroughly terminate all background servers and port listeners
function Stop-VoiceAgentProcesses {
    param([int]$VitePid = 0, [int]$TTSPid = 0)
    Write-Host ""
    Write-Host "[INFO] Stopping all background services and clearing ports..." -ForegroundColor Cyan

    if ($VitePid -and $VitePid -gt 0) {
        taskkill.exe /F /T /PID $VitePid 2>$null
    }
    if ($TTSPid -and $TTSPid -gt 0) {
        taskkill.exe /F /T /PID $TTSPid 2>$null
    }

    # Clean up any leftover listeners on ports 8086, 5173, 8765
    $ports = @(8086, 5173, 8765)
    foreach ($p in $ports) {
        try {
            $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
            if ($conns) {
                foreach ($c in $conns) {
                    if ($c.OwningProcess -and $c.OwningProcess -gt 0) {
                        taskkill.exe /F /T /PID $c.OwningProcess 2>$null
                    }
                }
            }
        } catch {}
    }

    # Clean up lingering pocket-tts processes if any
    Get-Process -Name "pocket-tts" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

# 3. Clean up before startup
Stop-VoiceAgentProcesses

# 4. Check if llama.cpp server is active on port 8085
$serverReady = $false
try {
    $res = Invoke-WebRequest -Uri "http://localhost:$Port/v1/models" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($res.StatusCode -eq 200) {
        $serverReady = $true
    }
} catch {
    $serverReady = $false
}

if (-not $serverReady) {
    Write-Host "[WARNING] llama.cpp server is NOT currently running on port $Port." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please start llama-server inside your WSL 2 terminal:" -ForegroundColor Yellow
    Write-Host "   ./llama-server -m /path/to/your/model.gguf --host 0.0.0.0 --port $Port -ngl 99 -c 32000" -ForegroundColor Green
    Write-Host ""
    
    $answer = Read-Host "Would you like to start the voice agent orchestrator anyway? (y/n)"
    if ($answer.ToLower() -ne 'y') {
        exit
    }
} else {
    Write-Host "[SUCCESS] Connected to llama.cpp server on port $Port!" -ForegroundColor Green
}

# 5. Start Pocket TTS Server with health check
Write-Host "[INFO] Starting Pocket TTS Server on port 8086 (Quantized)..." -ForegroundColor Cyan
$ttsLog = Join-Path $env:TEMP "pocket_tts.log"
$PocketTTSProcess = Start-Process cmd.exe -ArgumentList "/c .\venv311\Scripts\pocket-tts.exe serve --port 8086 --quantize > `"$ttsLog`" 2>&1" -NoNewWindow -PassThru

# Wait for Pocket TTS to be online (up to 15 seconds)
$ttsReady = $false
$ttsRetries = 0
while (-not $ttsReady -and $ttsRetries -lt 30) {
    Start-Sleep -Milliseconds 500
    $ttsRetries++
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:8086/docs" -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($res.StatusCode -eq 200) {
            $ttsReady = $true
        }
    } catch {}
}

if ($ttsReady) {
    Write-Host "[SUCCESS] Pocket TTS Server is online and ready on port 8086!" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Pocket TTS is taking longer than usual to start, continuing..." -ForegroundColor Yellow
}

# 6. Start React UI Dev Server with health check
Write-Host "[INFO] Starting React UI Dev Server on port 5173..." -ForegroundColor Cyan
$ViteProcess = Start-Process cmd.exe -ArgumentList "/c npm run dev --prefix ui-react" -NoNewWindow -PassThru

# Wait for Vite dev server to be online (up to 10 seconds)
$viteReady = $false
$viteRetries = 0
while (-not $viteReady -and $viteRetries -lt 20) {
    Start-Sleep -Milliseconds 500
    $viteRetries++
    try {
        $con = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
        if ($con) {
            $viteReady = $true
        }
    } catch {}
}

if ($viteReady) {
    Write-Host "[SUCCESS] React UI Dev Server is online on http://localhost:5173!" -ForegroundColor Green
}

# 7. Start Voice Agent Orchestrator with trap & finally safety
Write-Host ""
Write-Host "[INFO] Starting Voice Agent Orchestrator (main.py)..." -ForegroundColor Cyan
Write-Host ""

$vPid = if ($ViteProcess) { $ViteProcess.Id } else { 0 }
$tPid = if ($PocketTTSProcess) { $PocketTTSProcess.Id } else { 0 }

try {
    & ".\venv311\Scripts\python.exe" "main.py"
} catch {
    Write-Host "[INFO] Orchestrator stopped: $_" -ForegroundColor Yellow
} finally {
    Stop-VoiceAgentProcesses -VitePid $vPid -TTSPid $tPid
    Write-Host "[INFO] All services stopped cleanly. Goodbye!" -ForegroundColor Green
}
