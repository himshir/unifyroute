# UnifyRoute Setup Guide (Cross-Platform)

This guide covers how to set up UnifyRoute on Windows, macOS, and Linux.

## Prerequisites Verification

Before running setup, UnifyRoute automatically checks that all required prerequisites are installed. If any are missing, setup will stop and provide installation instructions.

### Auto-Check on Setup

When you run `./unifyroute setup` (or its equivalent), the system will:
1. Check for required prerequisites
2. Show which prerequisites are installed
3. Show which prerequisites need to be installed
4. Provide OS-specific installation instructions
5. Stop setup if any required prerequisites are missing

### Manual Prerequisite Check

You can also manually verify prerequisites at any time:

#### On Linux or macOS
```bash
# Using the shell wrapper (recommended)
./scripts/check_prerequisites.sh

# Or directly with Python
python3 scripts/check_prerequisites.py
```

#### On Windows
```bash
# Using the batch wrapper (recommended)
scripts\check_prerequisites.bat

# Or directly with Python
python scripts\check_prerequisites.py
py -3 scripts\check_prerequisites.py
```

## Required Prerequisites

| Tool | Minimum Version | Status |
|------|---|---|
| **Python** | 3.11+ | ✅ Required |
| **uv** | 0.1+ | ✅ Required |
| **Node.js** | 18+ | ✅ Required |
| **npm** | 9+ | ✅ Required |
| **Git** | 2.0+ | ✅ Required |

## Optional Prerequisites

| Tool | Minimum Version | Purpose |
|------|---|---|
| **Docker** | 20+ | Container deployment |
| **Docker Compose** | v2 | Multi-container orchestration |

## Quick Start by OS

### Windows

```cmd
# 1. Clone the repository
git clone https://github.com/unifyroute/UnifyRoute.git
cd UnifyRoute

# 2. Copy sample environment
copy sample.env .env

# 3. Run setup (using batch file)
unifyroute.bat setup

# 4. Start the application
unifyroute.bat start
```

**Alternative methods** (if batch file doesn't work):
```cmd
# Using Command syntax
unifyroute.cmd setup
unifyroute.cmd start

# Or direct Python
python unifyroute setup
python unifyroute start
```

👉 **For detailed Windows setup & troubleshooting**, see [Windows Setup Guide](WINDOWS_SETUP.md)

### macOS

```bash
# 1. Clone the repository
git clone https://github.com/unifyroute/UnifyRoute.git
cd UnifyRoute

# 2. Check prerequisites
./scripts/check_prerequisites.sh

# 3. Copy sample environment
cp sample.env .env

# 4. Run setup
./unifyroute setup

# 5. Start the application
./unifyroute start
```

### Linux

```bash
# 1. Clone the repository
git clone https://github.com/unifyroute/UnifyRoute.git
cd UnifyRoute

# 2. Check prerequisites
./scripts/check_prerequisites.sh

# 3. Copy sample environment
cp sample.env .env

# 4. Run setup
./unifyroute setup

# 5. Start the application
./unifyroute start
```

## Installation Instructions by OS

If any prerequisites are missing, the setup script will provide installation guidance. Below are the detailed instructions for each OS.

### Python 3.11+

#### Windows
```bash
# Download from: https://www.python.org/downloads/
# 1. Run the installer
# 2. Check: Add Python to PATH
# 3. Verify:
python --version
```

#### macOS
```bash
brew install python@3.11
python3.11 --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install python3.11
python3.11 --version
```

#### Linux (Fedora)
```bash
sudo dnf install python3.11
python3.11 --version
```

### uv (Dependency Manager)

#### Windows
```bash
# Option 1: Via pip
pip install uv

# Option 2: Download pre-built binary
# https://github.com/astral-sh/uv
# Add to PATH
```

#### macOS
```bash
# Option 1: Via Homebrew
brew install uv

# Option 2: Via curl
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Add ~/.local/bin to PATH (usually automatic)
```

### Node.js 18+

#### Windows
```bash
# Download from: https://nodejs.org/ (LTS version)
# 1. Run the installer
# 2. Add to PATH
# 3. Verify:
node --version
npm --version
```

#### macOS
```bash
brew install node@18
node --version
npm --version
```

#### Linux (Ubuntu/Debian)
```bash
# Option 1: Via NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Option 2: Via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
```

#### Linux (Fedora)
```bash
sudo dnf install nodejs npm
```

### Git 2.0+

#### Windows
```bash
# Download from: https://git-scm.com/download/win
# Run installer and add to PATH
git --version
```

#### macOS
```bash
brew install git
git --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install git
git --version
```

#### Linux (Fedora)
```bash
sudo dnf install git
```

### Docker (Optional)

#### Windows
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop
# 1. Run installer
# 2. Start Docker Desktop
# 3. Verify:
docker --version
docker compose version
```

#### macOS
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Or via Homebrew:
brew install docker docker-compose

# Verify:
docker --version
docker compose version
```

#### Linux (Ubuntu/Debian)
```bash
# Install Docker Engine
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify:
docker --version
docker compose version
```

#### Linux (Fedora)
```bash
sudo dnf install docker docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker

docker --version
docker compose version
```

## Setup Walkthrough

Once all prerequisites are installed, running setup is straightforward:

```bash
./unifyroute setup
```

The setup script will guide you through:
1. **Database Configuration** – SQLite path (or other backends)
2. **Application Settings** – Port, host, and API base URL
3. **Master Password** – For GUI login and CLI token operations
4. **Secrets Generation** – VAULT_MASTER_KEY and JWT_SECRET
5. **Configuration File** – Saves `.env` with your settings
6. **Virtual Environment** – Creates `.venv` for Python packages
7. **Dependencies** – Installs Python and Node.js packages
8. **Frontend Build** – Compiles the React GUI
9. **Database Migrations** – Sets up the database schema
10. **Admin Token** – Creates the initial API token

## Troubleshooting

### "Command not found" or "' is not recognized"

**Windows in Git Bash:**
```bash
# If ./unifyroute fails, use:
py -3 unifyroute setup
# or
python unifyroute setup
```

### Unicode/Encoding errors on Windows

Setup automatically configures UTF-8 output. If you still see encoding errors:
- Ensure you're using PowerShell 7+ or Windows Terminal
- Or set environment variable: `set PYTHONIOENCODING=utf-8`

### Prerequisites fail to install

If you get stuck on a specific prerequisite:
1. Run the prerequisite checker independently:
   ```bash
   python scripts/check_prerequisites.py
   ```
2. Note which prerequisite is failing
3. Refer to the detailed installation instructions above for that tool
4. Install it manually
5. Re-run setup

### "Cannot find Python executable"

Ensure python, python3, or py is in your PATH:
```bash
python --version
python3 --version
py -3 --version
```

At least one of these should work. If none do, install Python.

## Available Setup Commands

```bash
# First-time setup (interactive)
./unifyroute setup
python scripts/setup.py install

# Re-sync dependencies, rebuild GUI, run migrations
./unifyroute refresh
python scripts/setup.py refresh

# Clean up and remove local data
./unifyroute uninstall
python scripts/setup.py uninstall
```

## After Setup

### Start the Application

```bash
./unifyroute start
```

Default URLs:
- Dashboard/API root: `http://localhost:6565`
- OpenAI-compatible API: `http://localhost:6565/api/v1`

### Verify Installation

```bash
curl http://localhost:6565/api/v1/models
```

### Next Steps

1. Open the dashboard: http://localhost:6565
2. Log in with the master password you set during setup
3. Add provider credentials (OpenAI, Anthropic, etc.)
4. Configure routing tiers and fallback behavior
5. Start using the OpenAI-compatible endpoints

## Getting Help

For detailed setup information, see:
- [Installation Guide](../docs/installation.md)
- [Configuration Reference](../docs/configuration.md)
- [Getting Started](../docs/getting-started.md)
- [Support](../docs/SUPPORT.md)

For prerequisite checker details, see:
- [Prerequisite Checker Documentation](CHECK_PREREQUISITES.md)
