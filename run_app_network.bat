@echo off
echo ========================================
echo Business Knowledge Assistant - Local Network Access
echo ========================================
echo.
echo This script starts the app for LOCAL NETWORK access only.
echo (Same router/Wi-Fi network)
echo.
echo For EXTERNAL access (different networks/gateways):
echo - Use: run_app_with_ngrok.bat (recommended)
echo - Or see: EXTERNAL_NETWORK_ACCESS_GUIDE.md
echo.
echo ========================================
echo.

REM Get local IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
    goto :found
)
:found
set LOCAL_IP=%LOCAL_IP:~1%

echo Starting app...
echo.
echo To find your IP address, run: ipconfig
echo Look for "IPv4 Address" under your network adapter.
echo.
echo Access from other devices on SAME network:
echo   http://%LOCAL_IP%:8501
echo.
echo ========================================
echo Press Ctrl+C to stop the server.
echo ========================================
echo.
streamlit run app.py --server.address 0.0.0.0 --server.port 8501

