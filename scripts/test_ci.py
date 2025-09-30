#!/usr/bin/env python3
"""
Script to test CI configuration locally.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔄 {description}")
    print(f"Running: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(f"Output: {result.stdout[:200]}...")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Run CI tests locally."""
    print("🎯 Testing CI Configuration Locally")
    print("=" * 50)
    
    tests = [
        ("uv sync --dev", "Install dependencies"),
        ("uv run ruff check src/ tests/", "Code linting"),
        ("uv run ruff format --check src/ tests/", "Code formatting check"),
        ("uv run mypy src/gong/core/", "Type checking"),
        ("uv run pytest tests/unit/ -v --tb=short", "Unit tests"),
        ("uv run pytest tests/integration/test_demo.py -v", "Demo integration tests"),
        ("uv run gong --help", "CLI test"),
    ]
    
    results = []
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
    
    print("\n" + "=" * 50)
    print("📊 CI Test Results Summary")
    print("=" * 50)
    
    all_passed = True
    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All CI tests passed! Ready for deployment.")
        sys.exit(0)
    else:
        print("💥 Some CI tests failed. Please fix before committing.")
        sys.exit(1)


if __name__ == "__main__":
    main()