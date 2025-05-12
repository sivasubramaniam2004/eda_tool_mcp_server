#!/usr/bin/env python3
"""setup script for MCP server data science environment."""

import subprocess
import sys
import re
from pathlib import Path
import platform
import shutil

IS_INTERACTIVE = "--interactive" in sys.argv

def run_command(cmd, check=True):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e}")
        return None


def ask_permission(question):
    """Ask user for permission only if in interactive mode."""
    if not IS_INTERACTIVE:
        return True  # Always proceed in non-interactive mode

    while True:
        response = input(f"{question} (y/n): ").lower()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please answer 'y' or 'n'")

def check_uv():
    """Ensure uv is installed."""
    print("🔍 Checking for 'uv' installation...")
    uv_path = shutil.which("uv")
    if uv_path:
        print(f"✅ 'uv' is installed at: {uv_path}")
        return

    print("❗ 'uv' not found.")
    if ask_permission("Would you like to install 'uv'?"):
        print("⬇️ Installing uv...")
        result = run_command("curl -LsSf https://astral.sh/uv/install.sh | sh", check=False)
        if result is not None:
            print("✅ uv installed successfully.")
        else:
            sys.exit("❌ Failed to install 'uv'. Exiting.")
    else:
        sys.exit("❌ 'uv' is required to continue. Exiting.")


def setup_venv():
    """Create virtual environment if not present."""
    print("🔍 Checking for virtual environment...")
    if Path(".venv").exists():
        print("✅ Virtual environment already exists.")
        return

    if ask_permission("Virtual environment not found. Create one?"):
        print("Creating virtual environment using uv...")
        result = run_command("uv venv")
        if result is not None:
            print("✅ Virtual environment created successfully.")
        else:
            sys.exit("❌ Failed to create virtual environment. Exiting.")
    else:
        sys.exit("❌ Virtual environment is required to continue. Exiting.")


def sync_dependencies():
    """Sync dependencies from pyproject.toml."""
    print("Syncing dependencies from pyproject.toml...")
    run_command("uv sync")
    print("Dependencies synced successfully")


def build_package():
    """Build project and return wheel file path."""
    print("Building package with uv build...")
    process = subprocess.Popen(
        "uv build",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate()
    output = stdout + stderr

    if process.returncode != 0:
        sys.exit(f"Build failed with error code {process.returncode}:\n{stderr}")

    matches = re.findall(r'dist[\\/][^\s]+\.whl', output)
    whl_file = matches[-1] if matches else None
    if not whl_file:
        sys.exit("Failed to find wheel file in build output")

    path = Path(whl_file).absolute()
    print(f"Built wheel at {path}")
    return str(path)


def show_activation_hint():
    """Print virtual environment activation instructions."""
    print("\nTo activate your virtual environment manually:")
    if sys.platform.startswith("win"):
        print(r".venv\Scripts\activate")
    else:
        print("source .venv/bin/activate")


def main():
    print("=== MCP Server Environment Setup ===")

    check_uv()
    setup_venv()
    sync_dependencies()
    wheel_path = build_package()

    print("\n✅ Setup completed successfully.")
    print(f"✅ Wheel file created at: {wheel_path}")
    show_activation_hint()


if __name__ == "__main__":
    main()
