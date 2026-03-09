# Prerequisite Checker Improvements

## Issue Fixed
The prerequisite checker was reporting `npm` and `uv` as not found even though they were installed, especially when running from within a Python virtual environment.

## Root Causes
1. **npm detection** - npm is installed with Node.js but lives in a different directory on Windows (`AppData\Roaming\npm` or Node.js installation directory)
2. **uv detection** - uv installed via `pip install uv` becomes a Python module, not a direct PATH command
3. **Environment inheritance** - When `setup.py` spawned the prerequisite checker as a subprocess, the environment variables weren't being properly inherited

## Changes Made

### 1. Enhanced Command Detection (`check_prerequisites.py`)
- Added checks for `.cmd` variants on Windows (e.g., `npm.cmd`, `uv.cmd`)
- Added checks for common npm installation paths on Windows:
  - `%APPDATA%\npm`
  - `C:\Program Files\nodejs`
  - `C:\Program Files (x86)\nodejs`
- Added Python module check for `uv` (detects `python -m uv --version`)
- Added fallback checks for common installation directories

### 2. Enhanced Version Detection
- Updated `get_command_version()` to try command variants (`cmd.exe`, `.cmd`)
- Added Python module version detection for tools installed via pip
- Better error handling for version retrieval

### 3. Environment Inheritance in Setup
- Modified `check_prerequisites()` in `setup.py` to explicitly inherit parent environment: `env=os.environ.copy()`
- This ensures subprocesses can find tools installed in the current venv

## Result
Now detects:
- ✅ npm - Whether in PATH or in common Windows locations
- ✅ uv - Whether as system command or installed via pip
- ✅ All other prerequisites with improved robustness

## Test Results

### Before
```
Required: 3/5 met
✗ npm NOT FOUND
✗ uv NOT FOUND
```

### After
```
Required: 5/5 met
✓ Python 3.14.3
✓ uv 0.10.9 (installed via pip)
✓ Node.js v25.8.0
✓ npm 11.11.0
✓ Git 2.53.0
```

## Compatibility
- ✅ Windows - Handles .cmd variants and common installation paths
- ✅ macOS - Works with brew and standard installations
- ✅ Linux - Works with package managers and user installations
- ✅ Virtual Environments - Detects packages installed via pip in venv

## Files Modified
- `scripts/check_prerequisites.py` - Enhanced detection logic
- `scripts/setup.py` - Fixed environment inheritance in subprocess call
