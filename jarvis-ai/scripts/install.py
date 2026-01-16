#!/usr/bin/env python3
"""
JARVIS Dependency Installer

Installs all required dependencies for JARVIS AI Operating Layer.

Usage:
    python scripts/install.py           # Install all
    python scripts/install.py --core    # Core only (no AI)
    python scripts/install.py --minimal # Minimal for testing
"""

import subprocess
import sys
import argparse

# Core dependencies (always needed)
CORE_DEPS = [
    "numpy>=1.24.0",
    "psutil>=5.9.0",
    "pyautogui>=0.9.54",
    "pynput>=1.7.6",
    "pyperclip>=1.8.2",
    "mss>=9.0.0",
    "pillow>=10.0.0",
    "requests>=2.28.0",
    "pydantic>=2.0.0",
    "rich>=13.0.0",
    "python-dotenv>=1.0.0",
    "apscheduler>=3.10.0",
]

# AI/ML dependencies
AI_DEPS = [
    "ollama>=0.1.0",
    "openai-whisper>=20230314",
    "sounddevice>=0.4.6",
    "soundfile>=0.12.1",
]

# Audio dependencies (may need system libraries)
AUDIO_DEPS = [
    "pyaudio>=0.2.12",
    "webrtcvad>=2.0.10",
]

# Memory/Vector store dependencies
MEMORY_DEPS = [
    "chromadb>=0.4.0",
    "sentence-transformers>=2.0.0",
    "sqlalchemy>=2.0.0",
]

# Web server dependencies
SERVER_DEPS = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "aiohttp>=3.8.0",
]

# Windows-specific dependencies
WINDOWS_DEPS = [
    "pywin32>=306",
    "comtypes>=1.2.0",
]

# Development dependencies
DEV_DEPS = [
    "pytest>=7.4.0",
    "black>=23.0.0",
    "gitpython>=3.1.0",
]

# Optional enhancements
OPTIONAL_DEPS = [
    "edge-tts>=6.1.0",  # Fallback TTS
    "pyttsx3>=2.90",    # Another TTS fallback
    "opencv-python>=4.8.0",  # Vision features
]


def install_packages(packages: list, name: str, continue_on_error: bool = True):
    """Install a group of packages."""
    print(f"\n{'='*60}")
    print(f"Installing {name}...")
    print('='*60)

    failed = []
    for pkg in packages:
        try:
            print(f"  -> {pkg}")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            print(f"     [OK]")
        except subprocess.CalledProcessError as e:
            print(f"     [FAILED] {e}")
            failed.append(pkg)
            if not continue_on_error:
                raise

    if failed:
        print(f"\n  Warning: Failed to install: {', '.join(failed)}")

    return failed


def check_ollama():
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"\n[OK] Ollama is installed: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("\n[!] Ollama not found!")
    print("    Install from: https://ollama.ai/download")
    print("    After installing, run: ollama pull phi3:mini")
    return False


def main():
    parser = argparse.ArgumentParser(description="JARVIS Dependency Installer")
    parser.add_argument("--core", action="store_true", help="Install core only")
    parser.add_argument("--minimal", action="store_true", help="Minimal install")
    parser.add_argument("--dev", action="store_true", help="Include dev deps")
    parser.add_argument("--skip-audio", action="store_true", help="Skip audio deps")
    args = parser.parse_args()

    print("=" * 60)
    print("   JARVIS AI - Dependency Installer")
    print("=" * 60)
    print(f"Python: {sys.version}")

    all_failed = []

    # Always install core
    failed = install_packages(CORE_DEPS, "Core Dependencies")
    all_failed.extend(failed)

    if not args.minimal:
        # Memory
        failed = install_packages(MEMORY_DEPS, "Memory Dependencies")
        all_failed.extend(failed)

        # Server
        failed = install_packages(SERVER_DEPS, "Server Dependencies")
        all_failed.extend(failed)

        # Windows specific
        if sys.platform == "win32":
            failed = install_packages(WINDOWS_DEPS, "Windows Dependencies")
            all_failed.extend(failed)

    if not args.core and not args.minimal:
        # AI deps
        failed = install_packages(AI_DEPS, "AI Dependencies")
        all_failed.extend(failed)

        # Audio (optional, may fail)
        if not args.skip_audio:
            failed = install_packages(AUDIO_DEPS, "Audio Dependencies")
            all_failed.extend(failed)

    if args.dev:
        failed = install_packages(DEV_DEPS, "Development Dependencies")
        all_failed.extend(failed)

    # Check Ollama
    print("\n" + "=" * 60)
    print("Checking Ollama...")
    check_ollama()

    # Summary
    print("\n" + "=" * 60)
    print("Installation Summary")
    print("=" * 60)

    if all_failed:
        print(f"\n[!] Some packages failed to install:")
        for pkg in all_failed:
            print(f"    - {pkg}")
        print("\nTry installing them manually:")
        print(f"    pip install {' '.join(all_failed)}")
    else:
        print("\n[OK] All dependencies installed successfully!")

    print("\nNext steps:")
    print("  1. Start Ollama: ollama serve")
    print("  2. Pull model: ollama pull phi3:mini")
    print("  3. Run JARVIS: python main.py --text")
    print()


if __name__ == "__main__":
    main()
