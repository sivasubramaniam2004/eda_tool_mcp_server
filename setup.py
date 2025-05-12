#!/usr/bin/env python3
"""Setup script for MCP server data science environment without Claude setup."""

import json
import subprocess
import sys
from pathlib import Path
import re

import time

def run_command(cmd, check=True):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e}")
        return None


def ask_permission(question):
    """Ask user for permission."""
    while True:
        response = input(f"{question} (y/n): ").lower()
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please answer 'y' or 'n'")


def check_uv():
    """Check if uv is installed and install if needed."""
    if not run_command("which uv", check=False):
        if ask_permission("uv is not installed. Would you like to install it?"):
            print("Installing uv...")
            run_command("curl -LsSf https://astral.sh/uv/install.sh | sh")
            print("uv installed successfully")
        else:
            sys.exit("uv is required to continue")


def setup_venv():
    """Create virtual environment if it doesn't exist."""
    if not Path(".venv").exists():
        if ask_permission("Virtual environment not found. Create one?"):
            print("Creating virtual environment...")
            run_command("uv venv")
            print("Virtual environment created successfully")
        else:
            sys.exit("Virtual environment is required to continue")


def sync_dependencies():
    """Sync project dependencies."""
    print("Syncing dependencies...")
    run_command("uv sync")
    print("Dependencies synced successfully")


def build_package():
    """Build package and get wheel path."""
    print("Building package...")
    try:
        process = subprocess.Popen(
            "uv build",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()
        output = stdout + stderr
        print(f"Raw output: {output}")
    except Exception as e:
        sys.exit(f"Error running build: {str(e)}")

    if process.returncode != 0:
        sys.exit(f"Build failed with error code {process.returncode}")

    matches = re.findall(r'dist[\\/][^\s]+\.whl', output)
    whl_file = matches[-1] if matches else None
    if not whl_file:
        sys.exit("Failed to find wheel file in build output")

    path = Path(whl_file).absolute()
    print(f"Built wheel at {path}")
    return str(path)


def main():
    """Main setup function."""
    print("Starting setup...")
    check_uv()
    setup_venv()
    sync_dependencies()
    wheel_path = build_package()
    print("Setup completed successfully!")
    print(f"Wheel file available at: {wheel_path}")


if __name__ == "__main__":
    main()
