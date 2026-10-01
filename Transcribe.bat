@echo off
rem ===========================================================
rem  Double-click this file.
rem  It transcribes everything in  input\  into  output\
rem ===========================================================
setlocal
cd /d "%~dp0"
title Video to text

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if exist "%VENV_PY%" goto run

echo First run detected - installing everything into .venv.
echo This downloads about 4 GB and only happens once.
echo.
call "%~dp0setup.bat"
if errorlevel 1 exit /b 1
if not exist "%VENV_PY%" (
    echo Setup did not produce .venv\Scripts\python.exe - cannot continue.
    pause
    exit /b 1
)

:run
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo WARNING: ffmpeg is not on PATH. Video files will fail to load.
    echo          Fix with:  winget install Gyan.FFmpeg
    echo.
)

"%VENV_PY%" "%~dp0app.py"
exit /b %errorlevel%
