#!/usr/bin/env python3
"""
Health check script for the simulation platform.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import httpx


async def check_api_health(base_url: str = "http://localhost:8000") -> bool:
    """Check if the API server is healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/health")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print(f"✅ API server is healthy at {base_url}")
                    return True
                else:
                    print(f"❌ API server returned unhealthy status: {data}")
                    return False
            else:
                print(f"❌ API server returned status code: {response.status_code}")
                return False

    except httpx.ConnectError:
        print(f"❌ Cannot connect to API server at {base_url}")
        return False
    except httpx.TimeoutException:
        print(f"❌ Timeout connecting to API server at {base_url}")
        return False
    except Exception as e:
        print(f"❌ Error checking API health: {e}")
        return False


async def check_dependencies() -> bool:
    """Check if all required dependencies are available."""
    try:
        from gong.api.dependencies import get_dependencies

        deps = get_dependencies()

        print("🔍 Checking platform dependencies...")

        # Check template registry
        templates = await deps.template_registry.list_templates()
        if len(templates) > 0:
            print(f"✅ Template registry: {len(templates)} templates available")
        else:
            print("❌ Template registry: No templates found")
            return False

        # Check code generator
        from gong.core.models import ServiceDefinition

        test_service = ServiceDefinition(name="test-service")
        generated = await deps.code_generator.generate_service(test_service)
        if "src/main.py" in generated:
            print("✅ Code generator: Working")
        else:
            print("❌ Code generator: Failed to generate code")
            return False

        print("✅ All dependencies are working")
        return True

    except Exception as e:
        print(f"❌ Dependency check failed: {e}")
        return False


async def check_templates() -> bool:
    """Check if templates are working correctly."""
    try:
        from gong.templates.base import InMemoryTemplateRegistry

        registry = InMemoryTemplateRegistry()
        templates = await registry.list_templates()

        print(f"🔧 Found {len(templates)} templates:")
        for template_name in templates:
            print(f"  - {template_name}")

        # Test a template
        template = await registry.get_template("io/http_api_call")
        code = template.render(
            {"target_service": "test-service", "path": "/health", "method": "GET"}
        )

        if "test-service" in code:
            print("✅ Template rendering: Working")
            return True
        else:
            print("❌ Template rendering: Failed")
            return False

    except Exception as e:
        print(f"❌ Template check failed: {e}")
        return False


async def run_comprehensive_check() -> bool:
    """Run comprehensive health check."""
    print("🏥 Running comprehensive health check...")
    print("=" * 50)

    checks = [
        ("Dependencies", check_dependencies()),
        ("Templates", check_templates()),
        ("API Health", check_api_health()),
    ]

    results = []
    for name, check_coro in checks:
        print(f"\n📋 Checking {name}...")
        result = await check_coro
        results.append((name, result))

    print("\n" + "=" * 50)
    print("📊 Health Check Summary:")

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if not result:
            all_passed = False

    if all_passed:
        print("\n🎉 All health checks passed!")
        return True
    else:
        print("\n⚠️  Some health checks failed!")
        return False


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Health check for simulation platform")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API server URL")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive check")

    args = parser.parse_args()

    if args.comprehensive:
        success = await run_comprehensive_check()
    else:
        success = await check_api_health(args.api_url)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
