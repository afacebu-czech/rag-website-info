@echo off
echo ========================================
echo Business Knowledge Assistant - External Access
echo ========================================
echo.
echo This script starts the app with ngrok for external access.
echo.
echo Prerequisites:
echo 1. Install ngrok: https://ngrok.com/download
echo 2. Sign up for free ngrok account: https://dashboard.ngrok.com/signup
echo 3. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
echo 4. Configure ngrok: ngrok config add-authtoken YOUR_TOKEN
echo.
echo ========================================
echo.

REM Check if ngrok is installed
where ngrok >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: ngrok is not installed or not in PATH
    echo.
    echo Please install ngrok:
    echo 1. Download from: https://ngrok.com/download
    echo 2. Extract to a folder
    echo 3. Add to PATH or place ngrok.exe in this folder
    echo.
    pause
    exit /b 1
)

echo Starting Streamlit app...
start /B streamlit run app.py --server.address 0.0.0.0 --server.port 8501

REM Wait a moment for Streamlit to start
timeout /t 3 /nobreak >nul

echo.
echo Starting ngrok tunnel...
echo.
echo ========================================
echo IMPORTANT: Share the ngrok URL with users
echo ========================================
echo.
echo The URL will look like: https://xxxx-xxxx-xxxx.ngrok-free.app
echo.
echo Press Ctrl+C to stop both Streamlit and ngrok
echo.

ngrok http 8501

REM Cleanup if script exits
taskkill /F /IM streamlit.exe >nul 2>&1

