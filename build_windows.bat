@echo off
title ANV Viber Manager - Windows Builder
echo =======================================================
echo     ANV Viber Manager - Windows Builder Setup
echo =======================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH!
    echo Please install Python from https://www.python.org/downloads/
    echo and make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b
)

echo [1/3] Installing dependencies (requests, pillow, pyinstaller)...
python -m pip install --upgrade pip
pip install requests pillow pyinstaller

echo.
echo [2/3] Building single executable with PyInstaller...
pyinstaller --clean --onefile --noconsole --name "ANV-Viber-Manager" main.py

if %errorlevel% equ 0 (
    echo.
    echo =======================================================
    echo [SUCCESS] Build completed successfully!
    echo Your Windows application is located at:
    echo --^> dist\ANV-Viber-Manager.exe
    echo =======================================================
) else (
    echo.
    echo [ERROR] Build failed! Please check the output messages above.
)
echo.
pause
