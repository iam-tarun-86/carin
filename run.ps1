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

# Start React Dev Server in background
$ViteProcess = Start-Process cmd.exe -ArgumentList "/c npm run dev --prefix ui-react" -NoNewWindow -PassThru

try {
    & ".\venv311\Scripts\python.exe" "main.py"
} finally {
    if ($ViteProcess) {
        Write-Host ""
        Write-Host "[INFO] Stopping React dev server..." -ForegroundColor Cyan
        Stop-Process -Id $ViteProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
