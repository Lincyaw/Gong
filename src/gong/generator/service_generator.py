"""
Service code generator for microservices.
"""

from pathlib import Path
from typing import Any

import jinja2

from ..core.models import ServiceDefinition, WorkflowStep
from ..templates.loader import TemplateLoader


class ServiceCodeGenerator:
    """Generate FastAPI service code from service definitions."""

    def __init__(self, template_dir: str = None):
        self.template_loader = TemplateLoader(template_dir)

        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_loader.template_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def generate_service_code(self, service_def: ServiceDefinition, output_dir: Path):
        """Generate complete service code."""

        # Create directory structure
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)

        # Prepare template context
        context = self._prepare_template_context(service_def)

        # Generate main application file
        main_py = self._render_template("service/main.py.j2", context)
        (src_dir / "main.py").write_text(main_py)

        # Generate configuration file
        config_py = self._render_template("service/config.py.j2", context)
        (src_dir / "config.py").write_text(config_py)

        # Generate database utilities if needed
        if context["has_database"]:
            database_py = self._render_template("service/database.py.j2", context)
            (src_dir / "database.py").write_text(database_py)

        # Generate custom functions if needed
        if context["has_custom_functions"]:
            functions_py = self._render_template("service/functions.py.j2", context)
            (src_dir / "functions.py").write_text(functions_py)

        # Generate requirements.txt
        requirements = self._render_template("service/requirements.txt.j2", context)
        (output_dir / "requirements.txt").write_text(requirements)

        # Generate Dockerfile
        dockerfile = self._render_template("service/Dockerfile.j2", context)
        (output_dir / "Dockerfile").write_text(dockerfile)

        # Generate .dockerignore
        dockerignore = self._render_template("service/dockerignore.j2", context)
        (output_dir / ".dockerignore").write_text(dockerignore)

    def _prepare_template_context(self, service_def: ServiceDefinition) -> dict[str, Any]:
        """Prepare context data for template rendering."""

        # Analyze service dependencies
        has_database = self._has_database_dependencies(service_def)
        has_redis = self._has_redis_dependencies(service_def)
        has_custom_functions = self._has_custom_functions(service_def)

        # Get required Python packages
        required_packages = self._get_required_packages(service_def)

        # Process endpoints and workflows
        processed_endpoints = []
        for endpoint in service_def.endpoints:
            processed_endpoint = {
                "path": endpoint.path,
                "method": endpoint.method.lower(),
                "function_name": self._generate_function_name(endpoint.path),
                "workflow_steps": self._process_workflow_steps(endpoint.workflow, service_def),
                "has_path_params": "{" in endpoint.path,
                "path_params": self._extract_path_params(endpoint.path),
                "needs_request_body": endpoint.method.upper() in ["POST", "PUT", "PATCH"],
            }
            processed_endpoints.append(processed_endpoint)

        return {
            "service": service_def,
            "service_name": service_def.name,
            "namespace": getattr(service_def, "_namespace", "default"),
            "has_database": has_database,
            "has_redis": has_redis,
            "has_custom_functions": has_custom_functions,
            "required_packages": required_packages,
            "endpoints": processed_endpoints,
            "observability": service_def.observability,
            "resources": service_def.resources,
        }

    def _process_workflow_steps(
        self, workflow: list[WorkflowStep], service_def: ServiceDefinition
    ) -> list[dict[str, Any]]:
        """Process workflow steps for template rendering."""
        processed_steps = []

        for step in workflow:
            # Load template for this step
            template_config = self.template_loader.get_template_config(step.template)

            processed_step = {
                "name": step.name,
                "template": step.template,
                "params": step.params,
                "output": step.output,
                "inject_faults": step.inject_faults,
                "on_failure": step.on_failure,
                "template_config": template_config,
                "code_snippet": self._generate_step_code_snippet(step, template_config),
            }
            processed_steps.append(processed_step)

        return processed_steps

    def _generate_step_code_snippet(
        self, step: WorkflowStep, template_config: dict[str, Any]
    ) -> str:
        """Generate code snippet for a workflow step."""

        # Get the code template for this step type
        code_template_path = template_config.get("code_template")
        if not code_template_path:
            return f"        # TODO: Implement template {step.template}"

        # Prepare context for code template
        context = {"step": step, "params": step.params, "template_config": template_config}

        # Render the code template
        try:
            code_snippet = self._render_template(code_template_path, context)

            # Add fault injection if specified
            if step.inject_faults:
                fault_code = self._generate_fault_injection_code(step.inject_faults)
                code_snippet = fault_code + "\n" + code_snippet

            # Add output assignment if specified
            if step.output:
                code_snippet += f"\n        context['{step.output}'] = result"

            return code_snippet

        except Exception as e:
            return f"        # Error rendering template {step.template}: {e}"

    def _generate_fault_injection_code(self, faults) -> str:
        """Generate fault injection code."""
        try:
            fault_template = self._render_template(
                "snippets/fault_injection.py.j2", {"faults": faults}
            )
            return fault_template
        except Exception:
            # Fallback to simple fault injection
            return "        # Fault injection placeholder"

    def _render_template(self, template_path: str, context: dict[str, Any]) -> str:
        """Render a Jinja2 template."""
        try:
            template = self.jinja_env.get_template(template_path)
            return template.render(**context)
        except jinja2.TemplateNotFound:
            raise ValueError(f"Template not found: {template_path}")
        except Exception as e:
            raise ValueError(f"Error rendering template {template_path}: {e}")

    def _generate_function_name(self, path: str) -> str:
        """Generate function name from endpoint path."""
        func_name = path.replace("/", "_").replace("{", "").replace("}", "").strip("_")
        if func_name.startswith("v1_"):
            func_name = func_name[3:]
        return func_name or "root"

    def _extract_path_params(self, path: str) -> list[str]:
        """Extract path parameters from endpoint path."""
        import re

        return re.findall(r"\{(\w+)\}", path)

    def _get_required_packages(self, service_def: ServiceDefinition) -> list[str]:
        """Get list of required Python packages based on service definition."""
        packages = [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "httpx>=0.25.0",
            "pydantic>=2.4.0",
            "pydantic-settings>=2.0.0",
        ]

        # Add database dependencies
        if self._has_database_dependencies(service_def):
            packages.extend(
                [
                    "sqlalchemy[asyncio]>=2.0.0",
                    "asyncpg>=0.29.0",
                ]
            )

        # Add Redis dependencies
        if self._has_redis_dependencies(service_def):
            packages.extend(
                [
                    "redis[hiredis]>=5.0.0",
                ]
            )

        return list(set(packages))

    def _has_database_dependencies(self, service_def: ServiceDefinition) -> bool:
        """Check if service has database dependencies."""
        datastores = service_def.dependencies.get("datastores", [])
        for ds in datastores:
            if hasattr(ds, "type"):
                if ds.type in ["postgres", "mysql", "mongodb"]:
                    return True
            elif isinstance(ds, dict) and ds.get("type") in ["postgres", "mysql", "mongodb"]:
                return True
        return False

    def _has_redis_dependencies(self, service_def: ServiceDefinition) -> bool:
        """Check if service has Redis dependencies."""
        datastores = service_def.dependencies.get("datastores", [])
        for ds in datastores:
            if hasattr(ds, "type"):
                if ds.type == "redis":
                    return True
            elif isinstance(ds, dict) and ds.get("type") == "redis":
                return True
        return False

    def _has_custom_functions(self, service_def: ServiceDefinition) -> bool:
        """Check if service needs custom functions."""
        for endpoint in service_def.endpoints:
            for step in endpoint.workflow:
                if "custom_function" in step.template:
                    return True
        return False
