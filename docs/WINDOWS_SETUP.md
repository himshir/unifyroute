# UnifyRoute on Windows — Troubleshooting & Setup Guide

## Windows CLI Usage

On Windows, use one of these commands instead of `./unifyroute`:

### Option 1: Batch File (Recommended)
```cmd
unifyroute.bat setup
unifyroute.bat start
unifyroute.bat stop
unifyroute.bat get token
```

### Option 2: Command File
```cmd
unifyroute.cmd setup
unifyroute.cmd start
unifyroute.cmd stop
```

### Option 3: Direct Python (If batch files don't work)
```cmd
python unifyroute setup
python unifyroute start
python unifyroute get token
```

### Option 4: Git Bash (If you have Git Bash installed)
```bash
./unifyroute setup
./unifyroute start
./unifyroute get token
```

---

## Troubleshooting Web UI Not Coming Up

### 1. Verify the GUI was built during setup
The setup process should have run `npm run build` in the `gui/` directory. Check if the `gui/dist/` directory exists with these files:

```
gui/dist/
  ├── index.html
  ├── assets/
  └── vite.svg (or similar)
```

If `gui/dist/` is missing or empty, the GUI build failed. Fix it:

```cmd
cd gui
npm install
npm run build
cd ..
```

Then restart the application:
```cmd
unifyroute.bat start
```

### 2. Check if the launcher is running
Look at the logs to see if there were any errors:

```cmd
type logs/api.log
```

Common issues in logs:
- `GUI build not found at ...gui/dist` — Run the GUI build steps above
- `Address already in use` — Port 6565 is taken. Either:
  - Stop the existing process: `unifyroute.bat stop`
  - Change the port in `.env`: `PORT=6566`

### 3. Verify network connectivity
Make sure you can reach the launcher:

```cmd
curl http://localhost:6565
```

Or open in browser: `http://localhost:6565`

If the connection is refused:
- Check if the process is running: `tasklist | find "python"`
- Check the logs: `type logs/api.log`
- Verify port 6565 is not blocked by firewall

### 4. Clear browser cache
Sometimes the browser caches an old version of the GUI. Try:
- Press `Ctrl+Shift+Delete` to open Clear Browsing Data
- Clear cache, cookies, and site data
- Restart the application and refresh the page

### 5. Rebuild and restart
If the above doesn't work, try a complete refresh:

```cmd
unifyroute.bat setup refresh
unifyroute.bat start
```

---

## Full Setup on Windows (Step-by-Step)

### Prerequisites
Ensure you have installed:
- **Python 3.9+** — Download from [python.org](https://www.python.org/downloads/)
- **Node.js** (comes with npm) — Download from [nodejs.org](https://nodejs.org/)
- **Git** (optional but recommended) — Download from [git-scm.com](https://git-scm.com/)

Verify in Command Prompt:
```cmd
python --version
npm --version
git --version
```

### Step 1: Clone and Enter Directory
```cmd
git clone https://github.com/unifyroute/UnifyRoute.git
cd UnifyRoute
```

(Or download the ZIP file and extract it)

### Step 2: Run Setup
```cmd
unifyroute.bat setup
```

This will:
1. Create a `.env` file with configuration
2. Create a Python virtual environment (`.venv`)
3. Install Python dependencies
4. Build the GUI (`npm run build`)
5. Set up the database

### Step 3: Start the Application
```cmd
unifyroute.bat start
```

You should see:
```
🚀  Starting UnifyRoute...
ℹ️   Launcher starting on 0.0.0.0:6565
ℹ️   Logs → api.log
✅  UnifyRoute started (PID xxxx). Logs → api.log
ℹ️   Open: http://localhost:6565
```

### Step 4: Access the Dashboard
Open your browser and go to: **http://localhost:6565**

Log in with the master password you created during setup.

---

## Managing the Application

### Start the application
```cmd
unifyroute.bat start
```

### Stop the application
```cmd
unifyroute.bat stop
```

Or press `Ctrl+C` in the terminal if running in foreground.

### Restart the application
```cmd
unifyroute.bat restart
```

### View logs
```cmd
type logs/api.log
```

Or in PowerShell:
```powershell
Get-Content logs/api.log -Tail 50 -Wait
```

### Create a token
```cmd
unifyroute.bat create token admin
```

### Get your tokens
```cmd
unifyroute.bat get token
```

---

## Advanced: Custom Port or Host

Edit `.env` and change:
```env
PORT=6565
HOST=0.0.0.0
```

Then restart:
```cmd
unifyroute.bat restart
```

---

## FAQ

**Q: Why can't I use `./unifyroute` on Windows?**
A: The `./unifyroute` script is a POSIX shell script for macOS/Linux. Windows Command Prompt doesn't understand this format. Use `unifyroute.bat` instead.

**Q: The GUI is loading but shows errors connecting to `/api`**
A: This usually means the backend API failed to start. Check the logs:
```cmd
type logs/api.log
```

**Q: npm is installed but `unifyroute.bat setup` says npm is not found**
A: On Windows, npm can be in the Node.js installation directory. Run setup with Git Bash instead:
```bash
./unifyroute setup
```

**Q: Can I run UnifyRoute as a Windows Service?**
A: Not yet, but you can use Windows Task Scheduler to run `unifyroute.bat start` at startup. See [Service Integration Guide](docs/development.md#windows-service) for more details.

**Q: How do I uninstall UnifyRoute?**
A: Run:
```cmd
unifyroute.bat setup uninstall
```

This will stop services, remove virtual environment, and optionally back up configuration.

---

## Need More Help?

- Check [Getting Started Guide](../docs/getting-started.md)
- Check [Setup Guide](../SETUP_GUIDE.md)
- Check logs: `type logs/api.log`
- Open an issue: [GitHub Issues](https://github.com/unifyroute/UnifyRoute/issues)
