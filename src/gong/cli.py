"""
Command-line interface for the simulation platform.
"""

import asyncio
import json
from pathlib import Path

import click
import httpx
from pydantic import ValidationError

from .core.models import SimulationSpec
from .llm.architect import DummyLLMArchitect


@click.group()
def cli() -> None:
    """Microservice Simulation Platform CLI."""
    pass


@cli.command()
@click.option("--spec-file", "-f", help="Path to simulation spec YAML file")
@click.option("--prompt", "-p", help="Natural language prompt for LLM generation")
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def create(spec_file: str | None, prompt: str | None, api_url: str) -> None:
    """Create a new simulation."""

    if spec_file and prompt:
        click.echo("Error: Cannot specify both --spec-file and --prompt")
        return

    if not spec_file and not prompt:
        click.echo("Error: Must specify either --spec-file or --prompt")
        return

    try:
        if prompt:
            # Use LLM to generate config
            architect = DummyLLMArchitect()
            spec = await architect.generate_config(prompt)
        else:
            # Load from file
            import yaml

            if spec_file is None:
                click.echo("Error: spec_file is required")
                return

            with open(spec_file) as f:
                spec_data = yaml.safe_load(f)
            spec = SimulationSpec(**spec_data)

        # Submit to API
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{api_url}/api/v1/simulations", json=spec.dict())
            response.raise_for_status()
            result = response.json()

        click.echo(f"Simulation created: {result['simulation_id']}")
        click.echo(f"Status: {result['status']}")

    except ValidationError as e:
        click.echo(f"Validation error: {e}")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("simulation_id")
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def status(simulation_id: str, api_url: str) -> None:
    """Get simulation status."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/api/v1/simulations/{simulation_id}")
            response.raise_for_status()
            result = response.json()

        click.echo(f"Simulation: {result['name']}")
        click.echo(f"Status: {result['status']}")
        click.echo(f"Namespace: {result['namespace']}")
        click.echo(f"Created: {result['created_at']}")

        if result.get("topology"):
            click.echo("\nTopology:")
            click.echo(json.dumps(result["topology"], indent=2))

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            click.echo("Simulation not found")
        else:
            click.echo(f"API error: {e}")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def list(api_url: str) -> None:
    """List all simulations."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/api/v1/simulations")
            response.raise_for_status()
            simulations = response.json()

        if not simulations:
            click.echo("No simulations found")
            return

        click.echo("Simulations:")
        for sim in simulations:
            click.echo(f"  {sim['id']}: {sim['name']} ({sim['status']})")

    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("simulation_id")
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def delete(simulation_id: str, api_url: str) -> None:
    """Delete a simulation."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{api_url}/api/v1/simulations/{simulation_id}")
            response.raise_for_status()
            result = response.json()

        click.echo(result["message"])

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            click.echo("Simulation not found")
        else:
            click.echo(f"API error: {e}")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def templates(api_url: str) -> None:
    """List available templates."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/api/v1/templates")
            response.raise_for_status()
            template_list = response.json()

        click.echo("Available templates:")
        for template in template_list:
            click.echo(f"  {template}")

    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("simulation_id")
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def verify(simulation_id: str, api_url: str) -> None:
    """Verify simulation health."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{api_url}/api/v1/simulations/{simulation_id}/verify")
            response.raise_for_status()
            result = response.json()

        click.echo(f"Verification Status: {result['overall_status']}")
        click.echo(f"Timestamp: {result['timestamp']}")

        if "checks" in result:
            click.echo("\nDetailed Checks:")
            for check_name, check_result in result["checks"].items():
                status_icon = "✅" if check_result["status"] == "pass" else "❌"
                click.echo(f"  {status_icon} {check_name}: {check_result['status']}")

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            click.echo("Simulation not found")
        else:
            click.echo(f"API error: {e}")
    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("simulation_id")
@click.option("--pattern-file", "-f", help="Path to traffic pattern JSON file")
@click.option("--users", "-u", default=10, help="Number of users")
@click.option("--duration", "-d", default="5m", help="Duration (e.g., 5m, 30s)")
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def traffic(
    simulation_id: str, pattern_file: str, users: int, duration: str, api_url: str
) -> None:
    """Start traffic generation."""

    try:
        if pattern_file:
            import json

            with open(pattern_file) as f:
                pattern = json.load(f)
        else:
            pattern = {
                "type": "constant",
                "params": {"users": users, "duration": duration, "target_host": "order-service"},
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/v1/simulations/{simulation_id}/traffic", json=pattern
            )
            response.raise_for_status()
            result = response.json()

        click.echo(f"Traffic generation started: {result['traffic_job_id']}")

    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("simulation_id")
@click.option("--experiment-file", "-f", help="Path to chaos experiment JSON file")
@click.option("--type", "-t", default="pod-delete", help="Experiment type")
@click.option("--target", help="Target service")
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def chaos(
    simulation_id: str, experiment_file: str, type: str, target: str, api_url: str
) -> None:
    """Inject chaos experiment."""

    try:
        if experiment_file:
            import json

            with open(experiment_file) as f:
                experiment = json.load(f)
        else:
            experiment = {
                "type": type,
                "target": {"service": target} if target else {},
                "params": {"count": 1},
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_url}/api/v1/simulations/{simulation_id}/chaos", json=experiment
            )
            response.raise_for_status()
            result = response.json()

        click.echo(f"Chaos experiment started: {result['experiment_id']}")

    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("prompt")
@click.option("--api-url", default="http://localhost:8000", help="Platform API URL")
async def generate(prompt: str, api_url: str) -> None:
    """Generate simulation config from natural language."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{api_url}/api/v1/generate", json={"prompt": prompt})
            response.raise_for_status()
            result = response.json()

        click.echo("Generated configuration:")
        import json

        click.echo(json.dumps(result["generated_spec"], indent=2))

    except Exception as e:
        click.echo(f"Error: {e}")


@cli.command()
@click.argument("config_file", required=False)
@click.option("--prompt", "-p", help="Natural language prompt for LLM generation")
@click.option("--output-dir", "-o", help="Output directory for generated code")
@click.option("--save-config", "-s", is_flag=True, help="Save configuration to file")
async def generate_code(
    config_file: str | None, prompt: str | None, output_dir: str | None, save_config: bool
) -> None:
    """Generate microservices from configuration file or natural language prompt."""

    if config_file and prompt:
        click.echo("Error: Cannot specify both config file and prompt")
        return

    if not config_file and not prompt:
        click.echo("Error: Must specify either config file or prompt")
        return

    try:
        if config_file:
            # Use configuration file
            from .cli.config_generator import ConfigDrivenGenerator

            # Resolve config file path
            config_path = Path(config_file)
            if not config_path.is_absolute():
                config_path = Path.cwd() / config_path

            if not config_path.exists():
                click.echo(f"❌ Config file not found: {config_path}")
                return

            generator = ConfigDrivenGenerator()
            output_path = await generator.generate_from_config(str(config_path), output_dir)

            click.echo("\n🎉 Project generated successfully!")
            click.echo(f"📁 Project directory: {output_path}")
            click.echo("\n📋 Next steps:")
            click.echo(f"1. cd {output_path}")
            click.echo("2. ./deploy.sh")
            click.echo("3. ./test.sh")

        else:
            # Use natural language prompt
            from .llm.architect import DummyLLMArchitect

            architect = DummyLLMArchitect()
            spec = await architect.generate_config(prompt)

            click.echo(f"Generated simulation: {spec.name}")
            click.echo(f"Services: {len(spec.services)}")

            # Determine output directory
            if output_dir is None:
                output_dir = f"output/{spec.name}"

            # Save configuration if requested
            if save_config:
                import yaml

                config_path = Path(output_dir) / "simulation.yaml"
                config_path.parent.mkdir(parents=True, exist_ok=True)

                with open(config_path, "w", encoding="utf-8") as f:
                    yaml.dump(spec.model_dump(), f, default_flow_style=False)

                click.echo(f"📄 Saved configuration to {config_path}")

            # Generate code using config generator
            from .cli.config_generator import ConfigDrivenGenerator

            generator = ConfigDrivenGenerator()

            # Create temporary config file
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(spec.model_dump(), f, default_flow_style=False)
                temp_config = f.name

            try:
                output_path = await generator.generate_from_config(temp_config, output_dir)
                click.echo("\n✅ Code generation completed!")
                click.echo(f"📁 Output directory: {output_path}")
            finally:
                import os

                os.unlink(temp_config)

    except Exception as e:
        click.echo(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def main() -> None:
    """Main CLI entry point."""

    # Convert async commands to sync
    def make_sync(async_func):
        def sync_func(*args, **kwargs):
            return asyncio.run(async_func(*args, **kwargs))

        return sync_func

    # Wrap async commands
    for command in cli.commands.values():
        if asyncio.iscoroutinefunction(command.callback):
            command.callback = make_sync(command.callback)

    cli()


if __name__ == "__main__":
    main()
