"""
Template registry and management system.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from ..core.interfaces import Template, TemplateRegistry


@dataclass
class TemplateMetadata:
    """Template metadata structure."""

    name: str
    description: str
    category: str
    code_template: str
    input_schema: dict[str, str]
    output_schema: dict[str, str] | None = None
    dependencies: list[str] | None = None
    requires_custom_functions: bool = False
    version: str = "1.0.0"
    author: str | None = None
    tags: list[str] | None = None


class FileBasedTemplate(Template):
    """File-based template implementation."""

    def __init__(self, metadata: TemplateMetadata, template_dir: Path):
        self.metadata = metadata
        self.template_dir = template_dir
        self._jinja_env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def input_schema(self) -> dict[str, str]:
        return self.metadata.input_schema

    @property
    def output_schema(self) -> dict[str, str] | None:
        return self.metadata.output_schema

    def render(self, params: dict[str, Any], context_variable_name: str | None = None) -> str:
        """Render template with parameters."""
        try:
            template = self._jinja_env.get_template(self.metadata.code_template)

            # Prepare render context
            render_context = {
                **params,  # Direct parameter access
                "params": params,  # Nested parameter access
                "context_var": context_variable_name or "context",
                "metadata": self.metadata,
            }

            return template.render(**render_context)
        except Exception as e:
            raise RuntimeError(f"Failed to render template {self.name}: {e}")


class FileBasedTemplateRegistry(TemplateRegistry):
    """File-based template registry with hot-reloading support."""

    def __init__(self, template_dir: Path | None = None):
        if template_dir is None:
            template_dir = Path(__file__).parent / "files"

        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self._templates: dict[str, FileBasedTemplate] = {}
        self._registry_file = self.template_dir / "registry.yaml"

        # Initialize registry
        self._load_registry()

    def _load_registry(self) -> None:
        """Load template registry from file."""
        if not self._registry_file.exists():
            self._create_default_registry()

        with open(self._registry_file, encoding="utf-8") as f:
            registry_data = yaml.safe_load(f)

        self._templates.clear()

        for template_name, config in registry_data.get("templates", {}).items():
            try:
                metadata = TemplateMetadata(
                    name=template_name,
                    description=config.get("description", ""),
                    category=config.get("category", "misc"),
                    code_template=config["code_template"],
                    input_schema=config.get("input_schema", {}),
                    output_schema=config.get("output_schema"),
                    dependencies=config.get("dependencies", []),
                    requires_custom_functions=config.get("requires_custom_functions", False),
                    version=config.get("version", "1.0.0"),
                    author=config.get("author"),
                    tags=config.get("tags", []),
                )

                template = FileBasedTemplate(metadata, self.template_dir)
                self._templates[template_name] = template

            except Exception as e:
                print(f"Warning: Failed to load template {template_name}: {e}")

    def _create_default_registry(self) -> None:
        """Create default template registry."""
        default_registry = {
            "version": "1.0.0",
            "description": "Gong Template Registry",
            "templates": {
                "io/http_api_call": {
                    "description": "Make HTTP API call to another service",
                    "category": "io",
                    "code_template": "snippets/http_api_call.py.j2",
                    "input_schema": {"target_service": "str", "path": "str", "method": "str"},
                    "output_schema": {"api_response": "dict"},
                    "dependencies": ["httpx>=0.25.0"],
                    "version": "1.0.0",
                    "tags": ["http", "api", "network"],
                },
                "io/postgres_query": {
                    "description": "Execute PostgreSQL query",
                    "category": "io",
                    "code_template": "snippets/postgres_query.py.j2",
                    "input_schema": {"query": "str", "params": "list"},
                    "output_schema": {"query_result": "list"},
                    "dependencies": ["sqlalchemy[asyncio]>=2.0.0", "asyncpg>=0.29.0"],
                    "version": "1.0.0",
                    "tags": ["database", "postgres", "sql"],
                },
                "io/postgres_write": {
                    "description": "Execute PostgreSQL write operation",
                    "category": "io",
                    "code_template": "snippets/postgres_write.py.j2",
                    "input_schema": {"query": "str", "query_params": "list"},
                    "output_schema": {"write_result": "dict"},
                    "dependencies": ["sqlalchemy[asyncio]>=2.0.0", "asyncpg>=0.29.0"],
                    "version": "1.0.0",
                    "tags": ["database", "postgres", "sql", "write"],
                },
                "io/redis_get": {
                    "description": "Get value from Redis",
                    "category": "io",
                    "code_template": "snippets/redis_get.py.j2",
                    "input_schema": {"key": "str"},
                    "output_schema": {"redis_value": "str"},
                    "dependencies": ["redis[hiredis]>=5.0.0"],
                    "version": "1.0.0",
                    "tags": ["cache", "redis", "nosql"],
                },
                "io/redis_set": {
                    "description": "Set value in Redis",
                    "category": "io",
                    "code_template": "snippets/redis_set.py.j2",
                    "input_schema": {"key": "str", "value": "str", "ttl": "int"},
                    "output_schema": {"redis_result": "dict"},
                    "dependencies": ["redis[hiredis]>=5.0.0"],
                    "version": "1.0.0",
                    "tags": ["cache", "redis", "nosql", "write"],
                },
                "logic/custom_function_call": {
                    "description": "Call custom business logic function",
                    "category": "logic",
                    "code_template": "snippets/custom_function_call.py.j2",
                    "input_schema": {"functionName": "str", "arguments": "dict"},
                    "output_schema": {"function_result": "any"},
                    "requires_custom_functions": True,
                    "version": "1.0.0",
                    "tags": ["logic", "function", "custom"],
                },
                "security/jwt_token_validation": {
                    "description": "Validate JWT token",
                    "category": "security",
                    "code_template": "snippets/jwt_validation.py.j2",
                    "input_schema": {"token": "str", "jwks_url": "str"},
                    "output_schema": {"user_info": "dict"},
                    "dependencies": ["pyjwt>=2.8.0", "cryptography>=41.0.0"],
                    "version": "1.0.0",
                    "tags": ["security", "jwt", "auth"],
                },
                "control_flow/return_http_response": {
                    "description": "Return HTTP response",
                    "category": "control_flow",
                    "code_template": "snippets/return_response.py.j2",
                    "input_schema": {"status_code": "int", "body": "dict"},
                    "output_schema": {},
                    "version": "1.0.0",
                    "tags": ["http", "response", "control"],
                },
                "control_flow/parallel_execution": {
                    "description": "Execute multiple operations in parallel",
                    "category": "control_flow",
                    "code_template": "snippets/parallel_execution.py.j2",
                    "input_schema": {"branches": "list"},
                    "output_schema": {"parallel_results": "dict"},
                    "version": "1.0.0",
                    "tags": ["async", "parallel", "control"],
                },
            },
        }

        with open(self._registry_file, "w", encoding="utf-8") as f:
            yaml.dump(default_registry, f, default_flow_style=False, sort_keys=False)

    async def get_template(self, name: str) -> Template:
        """Get template by name."""
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found in registry")
        return self._templates[name]

    async def list_templates(self) -> list[str]:
        """List all available template names."""
        return list(self._templates.keys())

    async def register_template(self, template: Template) -> None:
        """Register a new template."""
        if isinstance(template, FileBasedTemplate):
            self._templates[template.name] = template
        else:
            raise ValueError("Only FileBasedTemplate instances can be registered")

    def get_templates_by_category(self, category: str) -> list[FileBasedTemplate]:
        """Get all templates in a specific category."""
        return [
            template
            for template in self._templates.values()
            if template.metadata.category == category
        ]

    def get_template_dependencies(self, template_name: str) -> list[str]:
        """Get dependencies for a template."""
        if template_name not in self._templates:
            return []

        template = self._templates[template_name]
        return template.metadata.dependencies or []

    def reload_registry(self) -> None:
        """Reload template registry from file."""
        self._load_registry()

    def get_registry_info(self) -> dict[str, Any]:
        """Get registry information."""
        with open(self._registry_file, encoding="utf-8") as f:
            registry_data = yaml.safe_load(f)

        return {
            "version": registry_data.get("version", "unknown"),
            "description": registry_data.get("description", ""),
            "template_count": len(self._templates),
            "categories": list(
                set(template.metadata.category for template in self._templates.values())
            ),
        }
