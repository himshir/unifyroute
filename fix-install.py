#!/usr/bin/env python3
"""
Quick fix script to install all dependencies in the virtual environment.
Run this if the web UI is not loading due to missing dependencies.
"""
import subprocess
import sys
from pathlib import Path

# Get paths
ROOT = Path(__file__).parent.resolve()

# Determine venv python
if sys.platform == "win32":
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
else:
    venv_python = ROOT / ".venv" / "bin" / "python"

if not venv_python.exists():
    print(f"❌ Virtual environment not found at {venv_python}")
    print("Run: unifyroute setup (or ./unifyroute setup)")
    sys.exit(1)

print("🔧 Fixing UnifyRoute installation...")
print(f"Using Python: {venv_python}")
print()

# Step 1: Upgrade pip
print("📦 Step 1/3: Upgrading pip...")
result = subprocess.run(
    [str(venv_python), "-m", "pip", "install", "-q", "--upgrade", "pip"],
    check=False
)
if result.returncode != 0:
    print("⚠️  pip upgrade had issues, but continuing...")

# Step 2: Install all local packages
print("📦 Step 2/3: Installing all packages in venv...")
for package_dir in ["shared", "api-gateway", "router", "launcher", "credential-vault", "quota-poller"]:
    pkg_path = ROOT / package_dir
    if pkg_path.exists():
        print(f"  Installing {package_dir}...")
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-q", "-e", str(pkg_path)],
            cwd=str(ROOT)
        )
        if result.returncode != 0:
            print(f"  ⚠️  {package_dir} install had issues")
    else:
        print(f"  ⏭️  {package_dir} not found (skipping)")

# Step 3: Install core dependencies
print("📦 Step 3/3: Installing core dependencies...")
core_packages = [
    "uvicorn", "fastapi", "sqlalchemy", "alembic", "redis",
    "pydantic", "httpx", "requests"
]
result = subprocess.run(
    [str(venv_python), "-m", "pip", "install", "-q"] + core_packages,
    check=False
)
if result.returncode != 0:
    print("  ⚠️  Some core packages failed to install")

print()
print("✅ Installation complete!")
print()
print("Next steps:")
print(f"  1. Start the app: unifyroute.bat start")
print(f"  2. Open: http://localhost:6565")
print()
print("If the web UI still doesn't load, check the logs:")
print(f"  type logs\\api.log")
