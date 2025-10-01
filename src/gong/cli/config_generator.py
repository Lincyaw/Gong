"""
YAML configuration-driven code generator.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader
from pydantic import ValidationError

from ..core.models import ServiceDefinition, SimulationSpec
from ..generator.service_generator import ServiceCodeGenerator
from ..orchestrator.k8s_generator import KubernetesManifestGenerator
from ..templates.registry import FileBasedTemplateRegistry


class ConfigDrivenGenerator:
    """Generate microservices from YAML configuration files."""

    def __init__(self, template_dir: Path | None = None) -> None:
        self.service_generator = ServiceCodeGenerator()
        self.k8s_generator = KubernetesManifestGenerator()

        # Initialize template system
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "templates" / "files"

        self.template_dir = Path(template_dir)
        self.template_registry = FileBasedTemplateRegistry(template_dir)

        # Initialize Jinja2 environment for file templates
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir), trim_blocks=True, lstrip_blocks=True
        )

    async def generate_from_config(self, config_file: str, output_dir: str | None = None) -> Path:
        """Generate complete project from YAML configuration file."""

        # Load and validate configuration
        spec = self._load_config(config_file)

        # Determine output directory
        if output_dir is None:
            output_dir = f"output/{spec.name}"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"🚀 Generating project: {spec.name}")
        print(f"📁 Output directory: {output_path}")
        print(f"🔧 Services: {len(spec.services)}")

        # Generate each service
        for service_def in spec.services:
            await self._generate_service(service_def, output_path, spec.name)

        # Generate global Kubernetes manifests
        await self._generate_global_manifests(spec, output_path)

        # Generate deployment scripts
        await self._generate_deployment_scripts(spec, output_path)

        print("\n✅ Project generation completed!")
        return output_path

    def _load_config(self, config_file: str) -> SimulationSpec:
        """Load and validate YAML configuration."""
        try:
            with open(config_file, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Validate against Pydantic model
            spec = SimulationSpec(**config_data)
            return spec

        except FileNotFoundError:
            raise ValueError(f"Configuration file not found: {config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")

    async def _generate_service(
        self, service_def: ServiceDefinition, output_path: Path, simulation_name: str
    ):
        """Generate code for a single service."""
        print(f"  🔧 Generating service: {service_def.name}")

        service_dir = output_path / service_def.name
        service_dir.mkdir(parents=True, exist_ok=True)

        # Set namespace for the service
        service_def._namespace = f"sim-{simulation_name}"

        # Generate service code
        await self.service_generator.generate_service_code(service_def, service_dir)

        # Generate Kubernetes manifests for this service
        await self.k8s_generator.generate_service_manifests(service_def, service_dir)

        print(f"    ✅ {service_def.name} generated")

    async def _generate_global_manifests(self, spec: SimulationSpec, output_path: Path):
        """Generate global Kubernetes manifests."""
        print("  🔧 Generating global Kubernetes manifests...")

        k8s_dir = output_path / "k8s"
        k8s_dir.mkdir(exist_ok=True)

        # Generate namespace using template
        namespace_template = self.jinja_env.get_template("k8s/namespace.yaml.j2")
        namespace_manifest = namespace_template.render(
            namespace=f"sim-{spec.name}",
            simulation_name=spec.name,
            timestamp=datetime.utcnow().isoformat(),
        )
        (k8s_dir / "namespace.yaml").write_text(namespace_manifest)

        # Generate datastores (databases, caches, etc.)
        await self._generate_datastore_manifests(spec, k8s_dir)

        print("    ✅ Global manifests generated")

    def _collect_datastores(self, spec: SimulationSpec) -> dict[str, dict[str, Any]]:
        """Collect all unique datastores from all services."""
        datastores = {}

        for service in spec.services:
            for datastore in service.dependencies.get("datastores", []):
                if hasattr(datastore, "name"):  # DatastoreDependency object
                    config = {
                        "name": datastore.name,
                        "type": datastore.type,
                        "provisioning": getattr(datastore, "provisioning", {}),
                        "resources": getattr(datastore, "resources", {}),
                        "persistence": getattr(datastore, "persistence", {}),
                    }
                    datastores[datastore.name] = config
                elif isinstance(datastore, dict):  # Dict format
                    config = {
                        "name": datastore["name"],
                        "type": datastore["type"],
                        "provisioning": datastore.get("provisioning", {}),
                        "resources": datastore.get("resources", {}),
                        "persistence": datastore.get("persistence", {}),
                    }
                    datastores[datastore["name"]] = config

        return datastores

    async def _generate_datastore_manifests(self, spec: SimulationSpec, k8s_dir: Path):
        """Generate manifests for all datastores using templates."""
        datastores = self._collect_datastores(spec)

        # Generate manifests for each unique datastore
        for name, config in datastores.items():
            try:
                datastore_type = config["type"]

                if datastore_type == "postgres":
                    template = self.jinja_env.get_template("k8s/postgres.yaml.j2")
                elif datastore_type == "redis":
                    template = self.jinja_env.get_template("k8s/redis.yaml.j2")
                else:
                    print(f"    ⚠️  Unknown datastore type: {datastore_type}, skipping {name}")
                    continue

                # Prepare template context
                context = {
                    "name": name,
                    "namespace": f"sim-{spec.name}",
                    "simulation_name": spec.name,
                    "resources": config.get("resources", {}),
                    "persistence": config.get("persistence", {}),
                    "replicas": config.get("replicas", 1),
                    "image": config.get("image"),
                    "database_name": config.get("database_name"),
                    "username": config.get("username"),
                    "password": config.get("password"),
                }

                manifest = template.render(**context)
                (k8s_dir / f"{name}.yaml").write_text(manifest)
                print(f"    📄 Generated {name}.yaml ({datastore_type})")

            except Exception as e:
                print(f"    ❌ Failed to generate manifest for {name}: {e}")
                import traceback

                traceback.print_exc()

    async def _generate_deployment_scripts(self, spec: SimulationSpec, output_path: Path):
        """Generate deployment and management scripts using templates."""
        print("  🔧 Generating deployment scripts...")

        # Prepare common context for all scripts
        datastores = self._collect_datastores(spec)
        context = {
            "simulation_name": spec.name,
            "namespace": f"sim-{spec.name}",
            "services": spec.services,
            "datastores": [
                {"name": name, "type": config["type"]} for name, config in datastores.items()
            ],
        }

        # Generate deploy.sh
        deploy_template = self.jinja_env.get_template("scripts/deploy.sh.j2")
        deploy_script = deploy_template.render(**context)
        deploy_path = output_path / "deploy.sh"
        deploy_path.write_text(deploy_script)
        deploy_path.chmod(0o755)

        # Generate cleanup.sh
        cleanup_template = self.jinja_env.get_template("scripts/cleanup.sh.j2")
        cleanup_script = cleanup_template.render(**context)
        cleanup_path = output_path / "cleanup.sh"
        cleanup_path.write_text(cleanup_script)
        cleanup_path.chmod(0o755)

        # Generate test.sh
        test_template = self.jinja_env.get_template("scripts/test.sh.j2")
        test_script = test_template.render(**context)
        test_path = output_path / "test.sh"
        test_path.write_text(test_script)
        test_path.chmod(0o755)

        print("    ✅ Deployment scripts generated")
