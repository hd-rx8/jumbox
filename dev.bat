@echo off
setlocal

title Jumbox - LAN File Transfer

echo ==========================================
echo         JUMBOX DEVELOPMENT MODE 
echo        LAN File Transfer System
echo ==========================================
echo.

REM ==========================================
REM 1. Check Python
REM ==========================================

echo [1/4] Verifying Python...

python --version >nul 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] Python was not found.
    echo.
    echo Install Python 3.11 or higher and try again.
    echo.
    pause
    exit /b 1
)

python --version
echo Python OK.
echo.

REM ==========================================
REM 2. Create virtual environment
REM ==========================================

echo [2/4] Verifying virtual environment...

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Creating .venv...
    echo.

    python -m venv .venv

    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment.
        echo.
        pause
        exit /b 1
    )

    echo Virtual environment created.
) else (
    echo Virtual environment found.
)

echo.

REM ==========================================
REM 3. Install dependencies
REM ==========================================

echo [3/4] Verifying dependencies...

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to update pip.
    echo.
    pause
    exit /b 1
)

python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    echo.
    pause
    exit /b 1
)

echo.
echo Dependencies OK.
echo.

REM ==========================================
REM 4. Start Jumbox
REM ==========================================

echo [4/4] Initiating Jumbox...
echo.
echo ==========================================
echo              JUMBOX ONLINE
echo ==========================================
echo.
echo Starting development server...
echo.
echo Access in your browser:
echo http://127.0.0.1:8000
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Jumbox was stopped.
echo.

pause
endlocal