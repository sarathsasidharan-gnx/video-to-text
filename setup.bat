@echo off
rem Creates .venv next to this file and installs everything app.py needs.
rem Safe to re-run; it just tops up anything missing.
setlocal
cd /d "%~dp0"

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if exist "%VENV_PY%" goto haveenv

echo Creating virtual environment in .venv ...
set "BOOTSTRAP=py -3"
where py >nul 2>&1 || set "BOOTSTRAP=python"
%BOOTSTRAP% -m venv ".venv"
if errorlevel 1 goto fail

:haveenv

echo Upgrading pip ...
"%VENV_PY%" -m pip install --upgrade pip --quiet
if errorlevel 1 goto fail

echo.
echo Installing WhisperX and PyTorch - roughly 4 GB, so give it a few minutes.
echo.
"%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto fail

echo.
echo Verifying the install ...
"%VENV_PY%" -c "import torch, whisperx; print('torch', torch.__version__)"
if errorlevel 1 goto fail

if not exist "%~dp0input"  mkdir "%~dp0input"
if not exist "%~dp0output" mkdir "%~dp0output"

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: ffmpeg was not found on PATH. Install it with:
    echo     winget install Gyan.FFmpeg
    echo then open a new window. Without ffmpeg, video files cannot be read.
)

echo.
echo Setup complete. Put files in input\ and double-click Transcribe.bat
exit /b 0

:fail
echo.
echo SETUP FAILED - see the messages above.
pause
exit /b 1
