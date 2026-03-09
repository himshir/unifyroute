@echo off
REM UnifyRoute Prerequisite Checker (Batch wrapper for Windows)
REM This wrapper enables running the prerequisite checker from Windows CMD

setlocal enabledelayedexpansion

REM Find the script directory
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%check_prerequisites.py"

REM Try to run with python, py, or python3
if exist "%PYTHON_SCRIPT%" (
    for %%p in (python py python3) do (
        where /q %%p
        if !errorlevel! equ 0 (
            %%p "%PYTHON_SCRIPT%" %*
            exit /b !errorlevel!
        )
    )
    
    REM If we get here, no Python was found
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.11 or later from https://www.python.org/downloads/
    exit /b 127
) else (
    echo Error: check_prerequisites.py not found at %PYTHON_SCRIPT%
    exit /b 1
)
