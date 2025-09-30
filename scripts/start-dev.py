#!/usr/bin/env python3
"""
Development startup script for the simulation platform.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import platform
        import uvicorn
        import fastapi
        import pydantic

        print("✅ Core dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please install dependencies with: uv sync")
        return False


def start_api_server():
    """Start the API server."""
    print("🚀 Starting API server...")

    # Set environment variables for development
    os.environ["USE_KUBERNETES"] = "false"
    os.environ["PYTHONPATH"] = str(project_root / "src")

    try:
        # Import and run the server
        from gong.api.main import app
        import uvicorn

        uvicorn.run(
            app, host="0.0.0.0", port=8000, reload=True, reload_dirs=[str(project_root / "src")]
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")


def run_demo():
    """Run the demo integration tests."""
    print("🎯 Running demo integration tests...")
    
    try:
        import pytest
        pytest.main([str(project_root / "tests" / "integration" / "test_demo.py"), "-v"])
    except ImportError:
        print("❌ pytest not installed. Install with: uv sync --dev")


def run_tests():
    """Run the test suite."""
    print("🧪 Running tests...")

    try:
        import pytest

        pytest.main([str(project_root / "tests"), "-v", "--tb=short"])
    except ImportError:
        print("❌ pytest not installed. Install with: uv add --dev pytest")


def show_help():
    """Show help information."""
    print("""
🎯 Microservice Simulation Platform - Development Helper

Usage: python scripts/start-dev.py [command]

Commands:
  server    Start the API server (default)
  demo      Run the demo script
  test      Run the test suite
  help      Show this help

Examples:
  python scripts/start-dev.py server
  python scripts/start-dev.py demo
  python scripts/start-dev.py test

Environment:
  - API server runs on http://localhost:8000
  - Uses dummy implementations for development
  - Auto-reload enabled for code changes

API Endpoints:
  - GET  /health                           - Health check
  - POST /api/v1/simulations              - Create simulation
  - GET  /api/v1/simulations              - List simulations
  - GET  /api/v1/simulations/{id}         - Get simulation
  - DELETE /api/v1/simulations/{id}       - Delete simulation
  - POST /api/v1/simulations/{id}/actions - Execute action
  - POST /api/v1/simulations/{id}/verify  - Verify simulation
  - GET  /api/v1/templates                - List templates
  - POST /api/v1/generate                 - Generate from prompt

CLI Commands:
  uv run simulation-platform create --prompt "Create an e-commerce app"
  uv run simulation-platform list
  uv run simulation-platform status <id>
  uv run simulation-platform verify <id>
  uv run simulation-platform delete <id>
""")


def main():
    """Main entry point."""
    if not check_dependencies():
        return 1

    command = sys.argv[1] if len(sys.argv) > 1 else "server"

    if command == "server":
        start_api_server()
    elif command == "demo":
        run_demo()
    elif command == "test":
        run_tests()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
