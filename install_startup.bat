@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo        Whistle Flow - Windows Startup Installer
echo ========================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET_VBS=%STARTUP_FOLDER%\Whistle_Flow.vbs"

echo Installing background auto-start runner to:
echo %TARGET_VBS%
echo.

copy /y "run_pill.vbs" "%TARGET_VBS%" >nul

if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Whistle Flow is now configured to start automatically on Windows boot!
    echo Hotkey: Ctrl + Space (Push-to-Talk or Tap-to-Lock)
) else (
    echo [ERROR] Failed to copy runner to Startup folder.
)

echo.
