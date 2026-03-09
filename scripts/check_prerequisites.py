#!/usr/bin/env python3
"""
UnifyRoute Prerequisite Checker
================================

A cross-platform script to verify that all project prerequisites are met
before running setup. Supports Windows, macOS, and Linux.

Usage:
    python3 scripts/check_prerequisites.py
    python scripts/check_prerequisites.py          (Windows)
    ./scripts/check_prerequisites.py                (Unix-like)
"""
from __future__ import annotations
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple

# Force UTF-8 encoding for output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# ── Colour helpers ─────────────────────────────────────────────────────────────
def colored(text: str, color: str) -> str:
    """Add ANSI colour codes (disabled on Windows CMD, enabled in PowerShell)."""
    if sys.platform == "win32" and not os.getenv("TERM"):
        return text
    
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors.get('reset', '')}"


def print_header(text: str):
    """Print a section header."""
    print(f"\n{colored(text, 'cyan')}")
    print(colored("=" * len(text), 'cyan'))


def print_success(text: str):
    """Print a success message."""
    print(f"{colored('✓', 'green')} {text}")


def print_warning(text: str):
    """Print a warning message."""
    print(f"{colored('⚠', 'yellow')} {text}")


def print_error(text: str):
    """Print an error message."""
    print(f"{colored('✗', 'red')} {text}")


def print_info(text: str):
    """Print an info message."""
    print(f"{colored('ℹ', 'cyan')} {text}")


# ── System detection ───────────────────────────────────────────────────────────
def get_os_type() -> str:
    """Return normalized OS type: 'windows', 'macos', or 'linux'."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    else:
        return system.lower()


def get_os_display() -> str:
    """Get human-readable OS name with version."""
    system = platform.system()
    version = platform.version()
    return f"{system} {version}"


# ── Check command availability ─────────────────────────────────────────────────
def command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH or common installation locations."""
    from shutil import which
    
    # First try standard PATH lookup
    if which(cmd) is not None:
        return True
    
    # Try to import as Python package (for tools like uv)
    if cmd == "uv":
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, OSError):
            pass
    
    # On Windows, try additional common locations
    if sys.platform == "win32":
        # Try .cmd variant (npm.cmd, uv.cmd, etc.)
        cmd_variant = which(f"{cmd}.cmd")
        if cmd_variant is not None:
            return True
        
        # Try common npm installation paths on Windows
        if cmd == "npm":
            common_paths = [
                Path.home() / "AppData" / "Roaming" / "npm" / f"{cmd}.cmd",
                Path("C:\\Program Files\\nodejs") / f"{cmd}.cmd",
                Path("C:\\Program Files (x86)\\nodejs") / f"{cmd}.cmd",
                Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps" / f"{cmd}.cmd",
            ]
            for path in common_paths:
                if path.exists():
                    return True
        
        # Try uv in home .local/bin (for pip install)
        if cmd == "uv":
            common_paths = [
                Path.home() / ".local" / "bin" / "uv.exe",
                Path.home() / "AppData" / "Local" / "uv" / "bin" / "uv.exe",
            ]
            for path in common_paths:
                if path.exists():
                    return True
    
    return False


def get_command_version(cmd: str, args: list[str] = None) -> Optional[str]:
    """
    Run a command with version flags and extract version.
    Try multiple command variants on Windows (cmd, .cmd, etc.)
    Also handles Python module versions (like uv installed via pip).
    """
    if args is None:
        args = ["--version"]
    
    # Build list of command variants to try
    commands_to_try = [cmd]
    if sys.platform == "win32":
        commands_to_try.extend([f"{cmd}.cmd", f"{cmd}.exe"])
    
    for cmd_variant in commands_to_try:
        try:
            result = subprocess.run(
                [cmd_variant] + args,
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = (result.stdout + result.stderr).strip()
            if output:
                return output.split('\n')[0]  # First line only
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    
    # Try as Python module (for tools installed via pip like uv)
    if cmd == "uv":
        try:
            result = subprocess.run(
                [sys.executable, "-m", "uv", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0 and output:
                return output.split('\n')[0]
        except (subprocess.TimeoutExpired, OSError):
            pass
    
    return None


def parse_version(version_string: str) -> Tuple[int, int, int]:
    """
    Parse a version string into (major, minor, patch) tuple.
    Handles common patterns like "v1.2.3", "1.2.3", "Python 3.11.0", etc.
    """
    # Extract all number sequences
    match = re.search(r'(\d+)(?:\.(\d+))?(?:\.(\d+))?', version_string)
    if not match:
        return (0, 0, 0)
    
    major = int(match.group(1)) if match.group(1) else 0
    minor = int(match.group(2)) if match.group(2) else 0
    patch = int(match.group(3)) if match.group(3) else 0
    
    return (major, minor, patch)


def version_meets_requirement(version: str, minimum: str) -> bool:
    """Check if version meets minimum requirement."""
    actual = parse_version(version)
    required = parse_version(minimum)
    return actual >= required

# ── Prerequisites definitions ──────────────────────────────────────────────────
@dataclass
class Prerequisite:
    """Definition of a prerequisite to check."""
    name: str                          # Display name
    command: str                       # Command to check
    minimum_version: str              # Minimum required version
    version_args: list[str] = None    # Args to get version
    required: bool = True              # Is this required?
    install_instructions: dict = None # OS-specific install instructions
    
    def __post_init__(self):
        if self.version_args is None:
            self.version_args = ["--version"]
        if self.install_instructions is None:
            self.install_instructions = {}


@dataclass
class CheckResult:
    """Result of a prerequisite check."""
    name: str
    required: bool
    met: bool
    version: Optional[str]
    minimum_version: str
    message: str


# ── Prerequisite checks ────────────────────────────────────────────────────────
def check_python(os_type: str) -> CheckResult:
    """Check Python version."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    minimum = "3.11"
    
    if version_meets_requirement(version, minimum):
        return CheckResult(
            name="Python",
            required=True,
            met=True,
            version=version,
            minimum_version=minimum,
            message=f"Python {version} is installed"
        )
    else:
        return CheckResult(
            name="Python",
            required=True,
            met=False,
            version=version,
            minimum_version=minimum,
            message=f"Python {version} does not meet minimum {minimum}"
        )


def check_command(
    name: str,
    cmd: str,
    minimum_version: str,
    version_args: list[str] = None,
    required: bool = True,
    install_url: str = None,
) -> CheckResult:
    """Generic command check."""
    if version_args is None:
        version_args = ["--version"]
    
    if not command_exists(cmd):
        return CheckResult(
            name=name,
            required=required,
            met=False,
            version=None,
            minimum_version=minimum_version,
            message=f"{cmd} command not found"
        )
    
    version = get_command_version(cmd, version_args)
    if not version:
        return CheckResult(
            name=name,
            required=required,
            met=False,
            version=None,
            minimum_version=minimum_version,
            message=f"Could not determine {name} version"
        )
    
    if version_meets_requirement(version, minimum_version):
        return CheckResult(
            name=name,
            required=required,
            met=True,
            version=version,
            minimum_version=minimum_version,
            message=f"{name} {version} is installed"
        )
    else:
        return CheckResult(
            name=name,
            required=required,
            met=False,
            version=version,
            minimum_version=minimum_version,
            message=f"{name} {version} does not meet minimum {minimum_version}"
        )


def check_docker_compose_v2(os_type: str) -> CheckResult:
    """Check for Docker Compose v2 (as a plugin, not standalone)."""
    if not command_exists("docker"):
        return CheckResult(
            name="Docker Compose v2",
            required=False,
            met=False,
            version=None,
            minimum_version="v2.0",
            message="Docker not found"
        )
    
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 and ("v2" in output or "2." in output):
            return CheckResult(
                name="Docker Compose v2",
                required=False,
                met=True,
                version="v2.0+",
                minimum_version="v2.0",
                message="Docker Compose v2 is available"
            )
    except (subprocess.TimeoutExpired, OSError):
        pass
    
    return CheckResult(
        name="Docker Compose v2",
        required=False,
        met=False,
        version=None,
        minimum_version="v2.0",
        message="Docker Compose v2 not available (required for Docker usage)"
    )


# ── Installation instructions ──────────────────────────────────────────────────
def get_install_instructions(name: str, os_type: str) -> Optional[str]:
    """Get OS-specific installation instructions."""
    instructions = {
        "Python": {
            "windows": (
                "Download from: https://www.python.org/downloads/\n"
                "  • Run the installer and check 'Add Python to PATH'\n"
                "  • Verify: python --version"
            ),
            "macos": (
                "Install via Homebrew:\n"
                "  $ brew install python@3.11\n"
                "  $ python3.11 --version"
            ),
            "linux": (
                "Install via your package manager:\n"
                "  Ubuntu/Debian: sudo apt-get install python3.11\n"
                "  Fedora: sudo dnf install python3.11\n"
                "  Arch: sudo pacman -S python"
            ),
        },
        "uv": {
            "windows": (
                "Install via pip or download from: https://github.com/astral-sh/uv\n"
                "  $ pip install uv\n"
                "  OR download pre-built binary and add to PATH"
            ),
            "macos": (
                "Install via Homebrew or curl:\n"
                "  $ brew install uv\n"
                "  OR: $ curl -LsSf https://astral.sh/uv/install.sh | sh"
            ),
            "linux": (
                "Install via curl:\n"
                "  $ curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                "  Then add ~/.local/bin to your PATH"
            ),
        },
        "Node.js": {
            "windows": (
                "Download from: https://nodejs.org/\n"
                "  • Use the LTS version (18+)\n"
                "  • Run installer and add to PATH\n"
                "  • Verify: node --version"
            ),
            "macos": (
                "Install via Homebrew:\n"
                "  $ brew install node@18\n"
                "  $ node --version"
            ),
            "linux": (
                "Install via NodeSource repository or nvm:\n"
                "  Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -\n"
                "  Then: sudo apt-get install -y nodejs\n"
                "  OR use nvm: https://github.com/nvm-sh/nvm"
            ),
        },
        "npm": {
            "windows": "npm is bundled with Node.js. Install Node.js from https://nodejs.org/",
            "macos": "npm is bundled with Node.js. Install via: brew install node@18",
            "linux": "npm is bundled with Node.js. Install via your package manager.",
        },
        "Docker": {
            "windows": (
                "Download Docker Desktop from: https://www.docker.com/products/docker-desktop\n"
                "  • Install and start Docker Desktop\n"
                "  • Verify: docker --version"
            ),
            "macos": (
                "Install Docker Desktop from: https://www.docker.com/products/docker-desktop\n"
                "  $ docker --version"
            ),
            "linux": (
                "Install via your package manager:\n"
                "  Ubuntu/Debian: sudo apt-get install docker.io docker-compose-plugin\n"
                "  Fedora: sudo dnf install docker docker-compose-plugin\n"
                "  Then enable: sudo systemctl start docker && sudo systemctl enable docker"
            ),
        },
        "Docker Compose v2": {
            "windows": (
                "Included with Docker Desktop 3.6+.\n"
                "  Download from: https://www.docker.com/products/docker-desktop\n"
                "  Verify: docker compose version"
            ),
            "macos": (
                "Included with Docker Desktop 3.6+.\n"
                "  Install: https://www.docker.com/products/docker-desktop\n"
                "  Command: docker compose version"
            ),
            "linux": (
                "Install as Docker plugin:\n"
                "  Ubuntu/Debian: sudo apt-get install docker-compose-plugin\n"
                "  Fedora: sudo dnf install docker-compose-plugin\n"
                "  Verify: docker compose version"
            ),
        },
        "Git": {
            "windows": (
                "Download from: https://git-scm.com/download/win\n"
                "  • Run installer and add to PATH\n"
                "  • Verify: git --version"
            ),
            "macos": (
                "Install via Homebrew:\n"
                "  $ brew install git\n"
                "  $ git --version"
            ),
            "linux": (
                "Install via package manager:\n"
                "  Ubuntu/Debian: sudo apt-get install git\n"
                "  Fedora: sudo dnf install git"
            ),
        },
    }
    
    if name in instructions:
        os_instructions = instructions[name].get(os_type)
        if os_instructions:
            return os_instructions
    
    return None


# ── Main checker ───────────────────────────────────────────────────────────────
def run_checks(os_type: str) -> Tuple[list[CheckResult], bool]:
    """Run all prerequisite checks. Returns (results, all_required_met)."""
    results = []
    
    # REQUIRED checks
    print_info("Checking required prerequisites...")
    results.append(check_python(os_type))
    results.append(check_command("uv", "uv", "0.1", required=True))
    results.append(check_command("Node.js", "node", "18.0", required=True))
    results.append(check_command("npm", "npm", "9.0", required=True))
    results.append(check_command("Git", "git", "2.0", required=True))
    results.append(check_command("Docker", "docker", "20.0", required=False))
    results.append(check_docker_compose_v2(os_type))
    
    # Check if all required prerequisites are met
    all_required_met = all(r.met for r in results if r.required)
    
    return results, all_required_met


def print_results(results: list[CheckResult], os_type: str):
    """Print check results with colors and installation guidance."""
    required_results = [r for r in results if r.required]
    optional_results = [r for r in results if not r.required]
    
    # REQUIRED section
    if required_results:
        print_header("Required Prerequisites")
        for result in required_results:
            if result.met:
                print_success(f"{result.name} {result.version}")
            else:
                print_error(f"{result.name} {result.version or 'NOT FOUND'} (need {result.minimum_version})")
    
    # OPTIONAL section
    if optional_results:
        print_header("Optional Prerequisites")
        for result in optional_results:
            if result.met:
                print_success(f"{result.name} {result.version}")
            else:
                print_warning(f"{result.name} {result.version or 'NOT FOUND'} (not available)")
    
    # Installation guidance
    print_header("Installation Guidance")
    missing = [r for r in results if not r.met]
    
    if not missing:
        print_success("All prerequisites are met!")
        return
    
    for result in missing:
        print(f"\n{colored(result.name, 'yellow')}")
        instructions = get_install_instructions(result.name, os_type)
        if instructions:
            for line in instructions.split('\n'):
                print(f"  {line}")
        else:
            print(f"  See: https://www.google.com/search?q=how+to+install+{result.name}")


def save_results_json(results: list[CheckResult], output_file: str = "prerequisites_check.json"):
    """Optionally save results as JSON for CI/CD integration."""
    data = {
        "timestamp": __import__('datetime').datetime.now().isoformat(),
        "os": get_os_display(),
        "os_type": get_os_type(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "prerequisites": [asdict(r) for r in results],
    }
    
    try:
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print_info(f"Results saved to: {output_file}")
    except IOError as e:
        print_warning(f"Could not save results to {output_file}: {e}")


def main():
    """Main entry point."""
    os_type = get_os_type()
    
    print_header(f"UnifyRoute Prerequisite Checker")
    print_info(f"Detected OS: {get_os_display()}")
    
    results, all_required_met = run_checks(os_type)
    print("\n")
    print_results(results, os_type)
    
    # Summary
    print_header("Summary")
    required_met = sum(1 for r in results if r.required and r.met)
    required_total = sum(1 for r in results if r.required)
    optional_met = sum(1 for r in results if not r.required and r.met)
    optional_total = sum(1 for r in results if not r.required)
    
    print(f"Required: {required_met}/{required_total} met")
    print(f"Optional: {optional_met}/{optional_total} met")
    
    # Optionally save JSON report (regardless of outcome)
    if "--json" in sys.argv or "-j" in sys.argv:
        save_results_json(results)
    
    if all_required_met:
        print(f"\n{colored('✓ Ready to run setup!', 'green')}")
        print_info("Run: ./unifyroute setup")
        return 0
    else:
        print(f"\n{colored('✗ Some required prerequisites are missing.', 'red')}")
        print_info("Please install the missing tools and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
