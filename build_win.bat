@echo off
title Build ANV Viber Manager for Windows
echo ======================================================
echo           Building ANV Viber Manager
echo ======================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from python.org and try again.
    goto end
)

:: Install PyInstaller if not present
echo [INFO] Checking and installing PyInstaller...
pip install pyinstaller

:: Clean old build folders
echo [INFO] Cleaning up old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: Build executable
echo [INFO] Compiling Python script into a standalone EXE...
pyinstaller --clean --onefile --noconsole --name "ANV Viber Manager" --add-data "viber_profiles;viber_profiles" viber_manager.py

if %errorlevel% equ 0 (
    echo.
    echo ======================================================
    echo [SUCCESS] Build completed successfully!
    echo The executable is located at: dist\ANV Viber Manager.exe
    echo ======================================================
) else (
    echo.
    echo [ERROR] Build failed! Please check the output logs above.
)

:end
echo.
pause
