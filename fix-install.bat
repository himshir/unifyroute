@echo off
REM Quick fix for UnifyRoute installation
REM This installs all dependencies in the virtual environment

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0

REM Find Python
set PYTHON=
for /f "delims=" %%i in ('where python 2^>nul') do set PYTHON=%%i
if "!PYTHON!"=="" (
    for /f "delims=" %%i in ('where python3 2^>nul') do set PYTHON=%%i
)
if "!PYTHON!"=="" (
    for /f "delims=" %%i in ('where py 2^>nul') do set PYTHON=%%i
)

if "!PYTHON!"=="" (
    echo Error: Python not found
    exit /b 127
)

REM Run the fix script
"%PYTHON%" "%SCRIPT_DIR%fix-install.py"
exit /b %ERRORLEVEL%
