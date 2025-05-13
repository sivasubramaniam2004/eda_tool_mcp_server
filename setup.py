#!/usr/bin/env python3
"""Cross-platform setup script for MCP server data science environment."""

import subprocess
import sys
import re
import shutil
from pathlib import Path
import platform
import os

IS_INTERACTIVE = "--interactive" in sys.argv
IS_WINDOWS = platform.system().lower() == "windows"
VENV_PATH = Path(".venv")
VENV_ACTIVATE = (
    VENV_PATH / "Scripts" / "activate.bat" if IS_WINDOWS else VENV_PATH / "bin" / "activate"
)


def run_command(cmd, check=True):
    """Run shell command and return stdout."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command '{cmd}': {e}")
        return None


def ask_permission(question):
    """Prompt user for y/n only in interactive mode."""
    if not IS_INTERACTIVE:
        return True
    while True:
        resp = input(f"{question} (y/n): ").lower()
        if resp in ['y', 'yes']:
            return True
        elif resp in ['n', 'no']:
            return False
        print("Please answer 'y' or 'n'")


def check_uv():
    """Ensure 'uv' is installed."""
    print("🔍 Checking for 'uv' installation...")
    if shutil.which("uv"):
        print("✅ 'uv' is installed.")
        return

    print("❗ 'uv' not found.")
    if ask_permission("Would you like to install 'uv'?"):
        install_cmd = "curl -LsSf https://astral.sh/uv/install.sh | sh"
        result = run_command(install_cmd, check=False)
        if result is not None:
            print("✅ 'uv' installed successfully.")
        else:
            sys.exit("❌ Failed to install 'uv'. Exiting.")
    else:
        sys.exit("❌ 'uv' is required to continue. Exiting.")


def setup_venv():
    """Create virtual environment if not present."""
    print("🔍 Checking for virtual environment...")
    if VENV_PATH.exists():
        print("✅ Virtual environment already exists.")
        return

    if ask_permission("Virtual environment not found. Create one?"):
        print("🐍 Creating virtual environment using uv...")
        result = run_command("uv venv")
        if result is not None:
            print("✅ Virtual environment created.")
        else:
            sys.exit("❌ Failed to create virtual environment. Exiting.")
    else:
        sys.exit("❌ Virtual environment is required. Exiting.")


def sync_dependencies():
    """Sync dependencies from pyproject.toml."""
    print("🔄 Syncing dependencies with uv...")
    result = run_command("uv sync")
    if result is not None:
        print("✅ Dependencies synced.")
    else:
        sys.exit("❌ Dependency sync failed. Exiting.")


def build_package():
    """Build project and return path to .whl file."""
    print("📦 Building package...")
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
        sys.exit(f"❌ Build failed:\n{stderr}")

    matches = re.findall(r'dist[\\/][^\s]+\.whl', output)
    if not matches:
        sys.exit("❌ Failed to find wheel file in output.")
    whl_path = Path(matches[-1]).resolve()
    print(f"✅ Built wheel: {whl_path}")
    return str(whl_path)


def show_activation_hint():
    """Print instructions to activate venv."""
    print("\n📌 To activate your virtual environment manually:")
    if IS_WINDOWS:
        print(r".venv\Scripts\activate")
    else:
        print("source .venv/bin/activate")


def activate_and_run_server():
    """Activate venv and run server."""
    print("🚀 Starting server...")

    # Build command to activate and run server
    activation_cmd = (
        f"{VENV_PATH}\\Scripts\\activate && cd src\\mcp_server_ds && python server.py --transport sse --host 127.0.0.1 --port 8000"
        if IS_WINDOWS else
        f"source {VENV_PATH}/bin/activate && cd src/mcp_server_ds && python server.py --transport sse --host 127.0.0.1 --port 8000"
    )

    subprocess.run(activation_cmd, shell=True)


def main():
    print("=== MCP Server Environment Setup ===")

    check_uv()
    setup_venv()
    sync_dependencies()
    wheel_path = build_package()

    print("\n✅ Setup completed successfully.")
    print(f"✅ Wheel file created: {wheel_path}")
    show_activation_hint()

    if ask_permission("\n🚀 Do you want to start the server now at http://127.0.0.1:8000/sse ?"):
        activate_and_run_server()


if __name__ == "__main__":
    main()
