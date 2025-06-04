@echo off
echo Starting Trading App (suppressing WebEngine warnings)...
echo.

REM Set environment variable to suppress WebEngine errors
set QTWEBENGINE_CHROMIUM_FLAGS=--disable-logging --disable-gpu-sandbox --no-sandbox

REM Change to app directory
cd /d "C:\Users\alanc\OneDrive\桌面\Python_Projects\trading_app"

REM Run the app with error suppression
C:\Users\alanc\anaconda3\envs\ib_trade\python.exe main.py 2>nul

pause