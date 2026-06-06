@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "MODEL_DIR=%ROOT%\models\medgemma-1.5-4b-it"
set "LOG_DIR=%ROOT%\logs"
set "FRONTEND_PORT=3000"
set "PUBLIC_MODE=0"
set "NGROK_CMD="

if /I "%~1"=="--help" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="--public" set "PUBLIC_MODE=1"

echo.
echo MedGemMA local launcher
echo Project: %ROOT%
echo.

if not exist "%BACKEND%\.venv\Scripts\python.exe" (
  echo ERROR: Backend Python venv was not found:
  echo   %BACKEND%\.venv\Scripts\python.exe
  echo.
  pause
  exit /b 1
)

if not exist "%FRONTEND%\package.json" (
  echo ERROR: Frontend package.json was not found:
  echo   %FRONTEND%\package.json
  echo.
  pause
  exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
  echo ERROR: Frontend dependencies were not found.
  echo Run this once:
  echo   cd /d "%FRONTEND%"
  echo   npm install
  echo.
  pause
  exit /b 1
)

if not exist "%MODEL_DIR%\config.json" (
  echo ERROR: MedGemMA model files were not found:
  echo   %MODEL_DIR%
  echo.
  echo Download them first:
  echo   cd /d "%ROOT%"
  echo   set HF_TOKEN=your_huggingface_token
  echo   .\backend\.venv\Scripts\python.exe .\scripts\download_medgemma.py
  echo.
  pause
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>nul

echo Starting backend and frontend in separate log windows...
echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo Logs:
echo   %LOG_DIR%\backend.log
echo   %LOG_DIR%\frontend.log
if "%PUBLIC_MODE%"=="1" echo   %LOG_DIR%\ngrok.log
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1" >nul 2>nul
if not errorlevel 1 (
  echo WARNING: Port 8000 is already in use. Backend window may show an address-in-use error.
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %FRONTEND_PORT% -ErrorAction SilentlyContinue | Select-Object -First 1" >nul 2>nul
if not errorlevel 1 (
  echo WARNING: Port %FRONTEND_PORT% is already in use. Frontend window may choose another port or fail.
)

start "MedGemMA Backend Logs" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_backend_logs.ps1" -Port 8000

start "MedGemMA Frontend Logs" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_frontend_logs.ps1" -Port %FRONTEND_PORT%

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:%FRONTEND_PORT%"

if "%PUBLIC_MODE%"=="1" (
  if exist "%ROOT%\ngrok.exe" set "NGROK_CMD=%ROOT%\ngrok.exe"
  if "%NGROK_CMD%"=="" (
    where ngrok >nul 2>nul
    if not errorlevel 1 set "NGROK_CMD=ngrok"
  )
  if "%NGROK_CMD%"=="" (
    echo.
    echo WARNING: ngrok.exe was not found in PATH.
    echo You can also put ngrok.exe next to this bat file.
    echo Install ngrok, then run:
    echo   run_local_medgemma.bat --public
  ) else (
    if not "%NGROK_AUTHTOKEN%"=="" (
      "%NGROK_CMD%" config add-authtoken "%NGROK_AUTHTOKEN%" >nul 2>nul
    )
    start "MedGemMA ngrok Public URL" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_ngrok_logs.ps1" -NgrokPath "%NGROK_CMD%" -Port %FRONTEND_PORT%
  )
)

echo Done. Keep the log windows open while you use the app.
echo Close those windows to stop the servers.
echo.
pause
exit /b 0

:help
echo Usage:
echo   run_local_medgemma.bat
echo   run_local_medgemma.bat --public
echo.
echo Starts local backend and frontend in separate visible log windows.
echo --public also starts ngrok http 3000 when ngrok.exe is installed.
echo Also writes logs to:
echo   logs\backend.log
echo   logs\frontend.log
echo   logs\ngrok.log
exit /b 0
