# UnifyRoute Prerequisite Checker

A cross-platform Python script that verifies all project prerequisites are installed before running `unifyroute setup`.

## Features

- ✅ **Cross-platform support**: Windows, macOS, and Linux
- 📋 **Detailed reporting**: Shows which prerequisites are met and which are missing
- 🔧 **OS-specific installation guidance**: Provides targeted instructions for each OS
- 🎯 **Required vs Optional checks**: Distinguishes between critical and optional tools
- 📊 **JSON export**: Optional CI/CD integration with `--json` flag
- 🎨 **Colorized output**: Easy-to-read colored terminal output

## Prerequisites Checked

### Required
- **Python 3.11+** – Core runtime
- **uv** – Fast Python dependency manager
- **Node.js 18+** – JavaScript runtime for GUI build
- **npm 9+** – Package manager for Node.js
- **Git 2.0+** – Version control

### Optional
- **Docker 20+** – Container runtime (for Docker deployment)
- **Docker Compose v2** – Multi-container orchestration

## Usage

### On Linux or macOS
```bash
# Using the shell wrapper (recommended)
./scripts/check_prerequisites.sh

# Or directly with Python
python3 scripts/check_prerequisites.py
```

### On Windows
```bash
# Using the batch wrapper (recommended)
scripts\check_prerequisites.bat

# Or directly with Python
python scripts\check_prerequisites.py
py -3 scripts\check_prerequisites.py
```

### Export Results as JSON
```bash
./scripts/check_prerequisites.sh --json
# or
python scripts/check_prerequisites.py -j
```

This creates `prerequisites_check.json` with detailed results for CI/CD pipelines.

## Output Example

```
UnifyRoute Prerequisite Checker
===============================
ℹ Detected OS: macOS 13.2.1
ℹ Checking required prerequisites...

Required Prerequisites
======================
✓ Python 3.11.0
✓ uv 0.1.22
✓ Node.js v18.15.0
✓ npm 9.5.0
✓ Git git version 2.39.2

Optional Prerequisites
======================
✓ Docker 24.0.0
✓ Docker Compose v2 Docker Compose version v2.16.0

Installation Guidance
=====================

Summary
=======
Required: 5/5 met
Optional: 2/2 met

✓ Ready to run setup!
ℹ Run: ./unifyroute setup
```

## Exit Codes

- **0** – All required prerequisites are met, ready to proceed with setup
- **1** – Some required prerequisites are missing, installation guidance provided
- **127** – Python interpreter not found

## Installation Guidance

If any prerequisites are missing, the script provides OS-specific installation instructions. For example:

### Installing uv

**macOS**
```bash
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then add ~/.local/bin to PATH
```

**Windows**
```bash
pip install uv
# or download from https://github.com/astral-sh/uv
```

### Installing Node.js

**macOS**
```bash
brew install node@18
```

**Linux**
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Windows**
Download from https://nodejs.org/ (LTS version)

## Integration with Setup Script

The prerequisite checker can be integrated into the main setup script to ensure dependencies are met:

```bash
#!/bin/bash
./scripts/check_prerequisites.sh
if [ $? -ne 0 ]; then
    echo "Please install missing prerequisites before proceeding."
    exit 1
fi

./unifyroute setup
```

Or in Python:

```python
import subprocess
import sys

result = subprocess.run(["python3", "scripts/check_prerequisites.py"])
if result.returncode != 0:
    print("Please install missing prerequisites before proceeding.")
    sys.exit(1)

# Proceed with setup
```

## Troubleshooting

### Script won't execute on macOS/Linux
```bash
# Make it executable
chmod +x scripts/check_prerequisites.sh
chmod +x scripts/check_prerequisites.py

# Then run it
./scripts/check_prerequisites.sh
```

### Python not found on Windows
Ensure Python is installed and added to PATH:
```bash
python --version  # Should show Python 3.11+
```

### Colors not showing in Windows CMD
- Uses automatic detection to disable colors in older terminals
- PowerShell 7+ will show full colors
- Use `--json` flag to get structured output for scripts

## JSON Output Format

When using `--json` or `-j` flags, output is saved as `prerequisites_check.json`:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "os": "macOS 13.2.1",
  "os_type": "macos",
  "python_version": "3.11.0",
  "prerequisites": [
    {
      "name": "Python",
      "required": true,
      "met": true,
      "version": "3.11.0",
      "minimum_version": "3.11",
      "message": "Python 3.11.0 is installed"
    },
    ...
  ]
}
```

## Contributing

To add or modify prerequisite checks:

1. Edit `scripts/check_prerequisites.py`
2. Add a new prerequisite check function following the `check_*` pattern
3. Call it from `run_checks()`
4. Update this README with the new requirement
5. Test on Windows, macOS, and Linux

## License

Apache License 2.0 (same as UnifyRoute)
