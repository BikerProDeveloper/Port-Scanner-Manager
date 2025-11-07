@echo off
cd /d "C:\Users\Jo\OneDrive\Documents\Web Development Portfolio\OmniStudio Proyect Manager\Projects\Port Scanner and Killer\PortScanner_ServerManager_FullFixed"

echo Starting Port Scanner & Server Manager...
echo.

REM Kill any existing Python processes
taskkill /f /im python.exe 2>nul

REM Start the single server on port 5502 (serves both API and HTML)
echo Starting server on port 5502...
start "Port Scanner Server" cmd /k "python server.py"

echo Waiting for server to start...
timeout /t 3 /nobreak >nul

REM Open the application in browser
echo Opening application in browser...
start "" "http://127.0.0.1:5502"

echo.
echo ✅ Full Application: http://127.0.0.1:5502
echo.
echo INSTRUCTIONS:
echo 1. Browser should open to http://127.0.0.1:5502
echo 2. API Base URL should already be set to: http://127.0.0.1:5502
echo 3. Click "Test Connection" - should show "Connected"
echo 4. Click "SCAN PORTS" - should show active ports
echo.
echo If browser doesn't open automatically, manually go to: http://127.0.0.1:5502
echo.
pause