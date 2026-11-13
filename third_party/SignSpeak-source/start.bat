@echo off
title SignSpeak - AI Sign Language Interpreter
color 0A
cd /d "%~dp0web"

echo.
echo   #####  ###  #####  #   #  #####  ####   #####   ###   #   #
echo  #        #  #       ##  #  #      #   #  #      #   #  #  #
echo   ####    #  #  ###  # # #  #####  ####   ####   #####  ###
echo       #   #  #     # #  ##      #  #      #      #   #  #  #
echo  #####   ###  #####  #   #  #####  #      #####  #   #  #   #
echo.
echo  ------------------------------------------------------------
echo    AI Sign Language Interpreter  -  100%% offline, on-device
echo  ------------------------------------------------------------
echo.

where npm >nul 2>nul
if errorlevel 1 (
    color 0C
    echo  [ERROR] Node.js / npm not found. Install from https://nodejs.org
    echo.
    pause
    exit /b 1
)

netstat -ano | findstr "LISTENING" | findstr /c:":4173 " >nul 2>nul
if not errorlevel 1 (
    echo  [OK] SignSpeak is already running - opening browser...
    start "" http://localhost:4173
    timeout /t 2 >nul
    exit /b 0
)

if not exist "node_modules" (
    echo  [SETUP] First run - installing dependencies, please wait...
    call npm install
    echo.
)

if not exist "..\frontend\index.html" (
    echo  [SETUP] Building the app...
    call npm run build
    echo.
)

echo  [1/2] Starting SignSpeak server on http://localhost:4173
echo  [2/2] Browser will open automatically when ready...
echo.
echo    TIP: Allow camera access when the browser asks.
echo    TIP: Works with Wi-Fi off - go ahead and prove it!
echo.
echo  Press Ctrl+C in this window to stop SignSpeak.
echo  ------------------------------------------------------------
echo.

start "" /min powershell -NoProfile -Command "for($i=0;$i -lt 30;$i++){try{Invoke-WebRequest http://localhost:4173 -UseBasicParsing -TimeoutSec 1 | Out-Null; Start-Process 'http://localhost:4173'; exit}catch{Start-Sleep 1}}"

call npm run preview -- --port 4173 --strictPort

echo.
echo  SignSpeak stopped.
pause
