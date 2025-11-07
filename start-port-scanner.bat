@echo off
chcp 65001 >nul
cd /d "C:\Users\Jo\OneDrive\Documents\Web Development Portfolio\OmniStudio Proyect Manager\Projects\Port Scanner and Killer\PortScanner_ServerManager_FullFixed"

echo Starting Port Scanner & Server Manager...
echo.

echo Killing old Python processes...
taskkill /f /im python.exe 2>nul

echo Starting server on port 5502...
start "Server" python server.py

echo Waiting 7 seconds for server to start...
timeout /t 7 /nobreak >nul

echo Opening browser...
start "" "http://127.0.0.1:5502"

echo.
echo If you see connection error, wait 10 seconds and refresh.
echo.
echo NEW: .bat File Generator and Advanced Servers!
echo.
pause