# PowerShell script to help set up ngrok for external access

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ngrok Setup Helper for External Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if ngrok is installed
$ngrokPath = Get-Command ngrok -ErrorAction SilentlyContinue

if (-not $ngrokPath) {
    Write-Host "ngrok is not installed or not in PATH." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To install ngrok:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://ngrok.com/download" -ForegroundColor White
    Write-Host "2. Extract ngrok.exe to a folder" -ForegroundColor White
    Write-Host "3. Add to PATH or place in this project folder" -ForegroundColor White
    Write-Host ""
    
    $install = Read-Host "Would you like to open the download page? (Y/N)"
    if ($install -eq "Y" -or $install -eq "y") {
        Start-Process "https://ngrok.com/download"
    }
    exit
}

Write-Host "ngrok is installed!" -ForegroundColor Green
Write-Host ""

# Check if authtoken is configured
$configPath = "$env:USERPROFILE\.ngrok2\ngrok.yml"
$hasAuthtoken = $false

if (Test-Path $configPath) {
    $configContent = Get-Content $configPath -Raw
    if ($configContent -match "authtoken") {
        $hasAuthtoken = $true
    }
}

if (-not $hasAuthtoken) {
    Write-Host "ngrok authtoken is not configured." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To configure:" -ForegroundColor Yellow
    Write-Host "1. Sign up at: https://dashboard.ngrok.com/signup" -ForegroundColor White
    Write-Host "2. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken" -ForegroundColor White
    Write-Host "3. Run: ngrok config add-authtoken YOUR_TOKEN" -ForegroundColor White
    Write-Host ""
    
    $openDashboard = Read-Host "Would you like to open the ngrok dashboard? (Y/N)"
    if ($openDashboard -eq "Y" -or $openDashboard -eq "y") {
        Start-Process "https://dashboard.ngrok.com/get-started/your-authtoken"
    }
    exit
}

Write-Host "ngrok is configured!" -ForegroundColor Green
Write-Host ""
Write-Host "You're ready to use external access!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the app with ngrok:" -ForegroundColor Cyan
Write-Host "  Run: run_app_with_ngrok.bat" -ForegroundColor White
Write-Host ""
Write-Host "Or manually:" -ForegroundColor Cyan
Write-Host "  1. Start Streamlit: streamlit run app.py --server.address 0.0.0.0 --server.port 8501" -ForegroundColor White
Write-Host "  2. Start ngrok: ngrok http 8501" -ForegroundColor White
Write-Host "  3. Share the ngrok URL with users" -ForegroundColor White
Write-Host ""

