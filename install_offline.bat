@echo off
rem ===========================================================
rem  OFFLINE install - no internet needed.
rem
rem  Requires, sitting next to this file:
rem     wheels\   - every package as a .whl  (from the Release)
rem     models\   - pre-downloaded Whisper models (from the Release)
rem
rem  Only prerequisite on the machine: Python 3.13 installed.
rem ===========================================================
setlocal
cd /d "%~dp0"

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if exist "%~dp0wheels" goto haswheels
echo ERROR: no wheels\ folder next to this script.
echo Download the offline bundle from the project's GitHub Releases page
echo and extract it here, so that wheels\ sits beside install_offline.bat
pause
exit /b 1
:haswheels

if exist "%VENV_PY%" goto haveenv
echo Creating virtual environment in .venv ...
set "BOOTSTRAP=py -3"
where py >nul 2>&1 || set "BOOTSTRAP=python"
%BOOTSTRAP% -m venv ".venv"
if errorlevel 1 goto fail
:haveenv

echo.
echo Installing from wheels\ - nothing is downloaded.
echo.
rem --no-index forbids reaching the network at all.
rem requirements.lock.txt pins the exact versions the wheels\ folder contains.
"%VENV_PY%" -m pip install --no-index --find-links "%~dp0wheels" -r "%~dp0requirements.lock.txt"
if errorlevel 1 goto fail

echo.
echo Verifying ...
"%VENV_PY%" -c "import torch, whisperx; print('torch', torch.__version__, '- OK')"
if errorlevel 1 goto fail

if not exist "%~dp0input"  mkdir "%~dp0input"
if not exist "%~dp0output" mkdir "%~dp0output"

if exist "%~dp0models" goto hasmodels
echo.
echo WARNING: no models\ folder found. The first transcription will try to
echo          download models from the internet. Copy models\ from the
echo          offline bundle if this machine has no network access.
goto checkff
:hasmodels
echo Models found in models\ - no download needed at run time.

:checkff
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: ffmpeg is not on PATH. Video files cannot be read without it.
    echo          Copy an ffmpeg build onto the machine and add it to PATH.
)

echo.
echo Offline install complete. Put files in input\ and run Transcribe.bat
pause
exit /b 0

:fail
echo.
echo INSTALL FAILED - see the messages above.
pause
exit /b 1
