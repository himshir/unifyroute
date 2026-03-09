@echo off
REM UnifyRoute CLI — Windows Command Wrapper
REM This script provides Windows cmd.exe compatibility for the UnifyRoute CLI
REM It delegates to the Python-based unifyroute script

setlocal enabledelayedexpansion

REM Get the directory where this command file is located
set SCRIPT_DIR=%~dp0

REM Try to find Python in order: python, python3, py
set PYTHON=
for /f "delims=" %%i in ('where python 2^>nul') do set PYTHON=%%i
if "!PYTHON!"=="" (
    for /f "delims=" %%i in ('where python3 2^>nul') do set PYTHON=%%i
)
if "!PYTHON!"=="" (
    for /f "delims=" %%i in ('where py 2^>nul') do set PYTHON=%%i
)

REM If we still don't have Python, error out
if "!PYTHON!"=="" (
    echo Error: Python interpreter not found. Install Python 3 and ensure python/py is on PATH.
    exit /b 127
)

REM Execute the Python-based unifyroute script with all arguments
"%PYTHON%" "%SCRIPT_DIR%unifyroute" %*
exit /b %ERRORLEVEL%
