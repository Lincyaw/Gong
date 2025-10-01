"""
Template loader for code generation.
"""

from pathlib import Path
from typing import Any

import yaml


class TemplateLoader:
    """Load and manage code generation templates."""

    def __init__(self, template_dir: str | None = None):
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default to templates directory relative to this file
            self.template_dir = Path(__file__).parent / "files"

        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Load template registry
        self.registry = self._load_template_registry()

    def _load_template_registry(self) -> dict[str, Any]:
        """Load template registry from registry.yaml."""
        registry_path = self.template_dir / "registry.yaml"

        if not registry_path.exists():
            # Create default registry
            default_registry = self._create_default_registry()
            with open(registry_path, "w") as f:
                yaml.dump(default_registry, f, default_flow_style=False)
            return default_registry

        with open(registry_path) as f:
            return yaml.safe_load(f)

    def _create_default_registry(self) -> dict[str, Any]:
        """Create default template registry."""
        return {
            "templates": {
                "io/http_api_call": {
                    "name": "HTTP API Call",
                    "description": "Make HTTP API call to another service",
                    "code_template": "snippets/http_api_call.py.j2",
                    "input_schema": {"target_service": "str", "path": "str", "method": "str"},
                    "output_schema": {"api_response": "dict"},
                    "dependencies": ["httpx>=0.25.0"],
                },
                "io/postgres_query": {
                    "name": "PostgreSQL Query",
                    "description": "Execute PostgreSQL query",
                    "code_template": "snippets/postgres_query.py.j2",
                    "input_schema": {"query": "str", "params": "list"},
                    "output_schema": {"query_result": "list"},
                    "dependencies": ["sqlalchemy[asyncio]>=2.0.0", "asyncpg>=0.29.0"],
                },
                "io/postgres_write": {
                    "name": "PostgreSQL Write",
                    "description": "Execute PostgreSQL write operation",
                    "code_template": "snippets/postgres_write.py.j2",
                    "input_schema": {"query": "str", "query_params": "list"},
                    "output_schema": {"write_result": "dict"},
                    "dependencies": ["sqlalchemy[asyncio]>=2.0.0", "asyncpg>=0.29.0"],
                },
                "io/redis_get": {
                    "name": "Redis GET",
                    "description": "Get value from Redis",
                    "code_template": "snippets/redis_get.py.j2",
                    "input_schema": {"key": "str"},
                    "output_schema": {"redis_value": "str"},
                    "dependencies": ["redis[hiredis]>=5.0.0"],
                },
                "io/redis_set": {
                    "name": "Redis SET",
                    "description": "Set value in Redis",
                    "code_template": "snippets/redis_set.py.j2",
                    "input_schema": {"key": "str", "value": "str", "ttl": "int"},
                    "output_schema": {"redis_result": "dict"},
                    "dependencies": ["redis[hiredis]>=5.0.0"],
                },
                "logic/custom_function_call": {
                    "name": "Custom Function Call",
                    "description": "Call custom business logic function",
                    "code_template": "snippets/custom_function_call.py.j2",
                    "input_schema": {"functionName": "str", "arguments": "dict"},
                    "output_schema": {"function_result": "any"},
                    "requires_custom_functions": True,
                },
                "security/jwt_token_validation": {
                    "name": "JWT Token Validation",
                    "description": "Validate JWT token",
                    "code_template": "snippets/jwt_validation.py.j2",
                    "input_schema": {"token": "str", "jwks_url": "str"},
                    "output_schema": {"user_info": "dict"},
                    "dependencies": ["pyjwt>=2.8.0", "cryptography>=41.0.0"],
                },
                "control_flow/return_http_response": {
                    "name": "Return HTTP Response",
                    "description": "Return HTTP response",
                    "code_template": "snippets/return_response.py.j2",
                    "input_schema": {"status_code": "int", "body": "dict"},
                    "output_schema": {},
                },
                "control_flow/parallel_execution": {
                    "name": "Parallel Execution",
                    "description": "Execute multiple operations in parallel",
                    "code_template": "snippets/parallel_execution.py.j2",
                    "input_schema": {"branches": "list"},
                    "output_schema": {"parallel_results": "dict"},
                },
            }
        }

    def get_template_config(self, template_name: str) -> dict[str, Any]:
        """Get configuration for a template."""
        templates = self.registry.get("templates", {})
        return templates.get(
            template_name,
            {
                "name": f"Unknown Template: {template_name}",
                "description": f"Template {template_name} not found in registry",
                "code_template": None,
            },
        )

    def list_templates(self) -> dict[str, dict[str, Any]]:
        """List all available templates."""
        return self.registry.get("templates", {})

    def add_template(self, template_name: str, config: dict[str, Any]):
        """Add a new template to the registry."""
        if "templates" not in self.registry:
            self.registry["templates"] = {}

        self.registry["templates"][template_name] = config

        # Save updated registry
        registry_path = self.template_dir / "registry.yaml"
        with open(registry_path, "w") as f:
            yaml.dump(self.registry, f, default_flow_style=False)

    def validate_template(self, template_name: str) -> bool:
        """Validate that a template exists and has required files."""
        config = self.get_template_config(template_name)

        if not config.get("code_template"):
            return False

        template_path = self.template_dir / config["code_template"]
        return template_path.exists()

    def get_template_path(self, template_name: str) -> Path | None:
        """Get the file path for a template."""
        config = self.get_template_config(template_name)
        code_template = config.get("code_template")

        if not code_template:
            return None

        return self.template_dir / code_template
