@echo off
setlocal

title Jumbox - LAN File Transfer

echo ==========================================
echo              JUMBOX
echo        LAN File Transfer System
echo ==========================================
echo.

echo Verifying Docker...

docker info >nul 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] Docker is not running or not installed.
    echo.
    echo Open Docker Desktop and try again.
    pause
    exit /b 1
)

echo Docker OK.
echo.
echo Starting Jumbox...
echo.
echo Press Ctrl+C to stop Jumbox and close the application.

docker compose up --build

pause
endlocal