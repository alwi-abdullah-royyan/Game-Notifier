@echo off
set ROOT=%~dp0..
set PID_FILE=%ROOT%\data\game-notifier.pid
if not exist "%PID_FILE%" (
    echo game-notifier does not appear to be running (no PID file found).
    exit /b 1
)
set /p APP_PID=<"%PID_FILE%"
echo Stopping game-notifier (PID %APP_PID%)...
taskkill /F /PID %APP_PID% >nul 2>&1
del "%PID_FILE%" >nul 2>&1
echo Done.
