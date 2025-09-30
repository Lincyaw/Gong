"""
Base template implementations and registry.
"""

from typing import Any

from jinja2 import BaseLoader, Environment

from ..core.interfaces import Template, TemplateRegistry


class BaseTemplate(Template):
    """Base implementation of Template interface."""

    def __init__(
        self,
        name: str,
        template_code: str,
        input_schema: dict[str, str],
        output_schema: dict[str, str] | None = None,
    ):
        self._name = name
        self._template_code = template_code
        self._input_schema = input_schema
        self._output_schema = output_schema
        self._jinja_env = Environment(loader=BaseLoader())

    @property
    def name(self) -> str:
        return self._name

    @property
    def input_schema(self) -> dict[str, str]:
        return self._input_schema

    @property
    def output_schema(self) -> dict[str, str] | None:
        return self._output_schema

    def render(self, params: dict[str, Any], context_variable_name: str | None = None) -> str:
        """Render template with parameters."""
        template = self._jinja_env.from_string(self._template_code)
        # Make params available both directly and under 'params' key for backward compatibility
        render_context = {
            **params,  # Direct access to parameters
            "params": params,  # Nested access for complex templates
            "context_var": context_variable_name or "context",
        }
        return template.render(**render_context)


class InMemoryTemplateRegistry(TemplateRegistry):
    """In-memory template registry implementation."""

    def __init__(self):
        self._templates: dict[str, Template] = {}
        self._initialize_builtin_templates()

    async def get_template(self, name: str) -> Template:
        """Get template by name."""
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found")
        return self._templates[name]

    async def list_templates(self) -> list[str]:
        """List all available template names."""
        return list(self._templates.keys())

    async def register_template(self, template: Template) -> None:
        """Register a new template."""
        self._templates[template.name] = template

    def _initialize_builtin_templates(self) -> None:
        """Initialize built-in templates."""
        # HTTP API Call template
        api_call_template = BaseTemplate(
            name="io/http_api_call",
            template_code="""
# HTTP API call to {{ params.target_service }}
async with httpx.AsyncClient() as client:
    response = await client.{{ params.method|lower }}(
        f"http://{{ params.target_service }}.{namespace}.svc.cluster.local{{ params.path }}",
        {% if params.json %}json={{ params.json }},{% endif %}
        {% if params.headers %}headers={{ params.headers }},{% endif %}
        timeout=30.0
    )
    response.raise_for_status()
    {% if output_schema %}{{ context_var }}["{{ params.output or 'api_response' }}"] = response.json(){% endif %}
""",
            input_schema={"target_service": "str", "path": "str", "method": "str"},
            output_schema={"api_response": "dict"},
        )

        # Database query template
        db_query_template = BaseTemplate(
            name="io/postgres_query",
            template_code="""
# Database query
async with get_db_connection("{{ params.datastore_name }}") as conn:
    {% if params.query_params %}
    result = await conn.fetch("{{ params.query }}", {{ params.query_params|join(', ') }})
    {% else %}
    result = await conn.fetch("{{ params.query }}")
    {% endif %}
    {% if output_schema %}{{ context_var }}["{{ params.output or 'query_result' }}"] = [dict(row) for row in result]{% endif %}
""",
            input_schema={"datastore_name": "str", "query": "str"},
            output_schema={"query_result": "list"},
        )

        # JWT validation template
        jwt_template = BaseTemplate(
            name="security/jwt_validation",
            template_code="""
# JWT token validation
import jwt
from jwt import PyJWKSClient

try:
    jwks_client = PyJWKSClient("{{ params.jwks_url }}")
    signing_key = jwks_client.get_signing_key_from_jwt({{ params.token }})
    decoded_token = jwt.decode(
        {{ params.token }},
        signing_key.key,
        algorithms=["RS256"],
        audience="{{ params.audience or 'api' }}"
    )
    {% if output_schema %}{{ context_var }}["{{ params.output or 'user_claims' }}"] = decoded_token{% endif %}
except jwt.InvalidTokenError:
    {% if params.on_failure %}{{ params.on_failure }}{% else %}raise HTTPException(status_code=401, detail="Invalid token"){% endif %}
""",
            input_schema={"token": "str", "jwks_url": "str"},
            output_schema={"user_claims": "dict"},
        )

        # Return HTTP response template
        response_template = BaseTemplate(
            name="control_flow/return_response",
            template_code="""
# Return HTTP response
return JSONResponse(
    status_code={{ params.status_code or 200 }},
    content={{ params.body or '{}' }}
)
""",
            input_schema={"status_code": "int", "body": "dict"},
        )

        # Redis operations template
        redis_get_template = BaseTemplate(
            name="io/redis_get",
            template_code="""
# Redis GET operation
import redis.asyncio as redis
redis_client = redis.from_url("redis://{{ params.datastore_name }}.{namespace}.svc.cluster.local:6379")
try:
    result = await redis_client.get("{{ params.key }}")
    {% if output_schema %}{{ context_var }}["{{ params.output or 'redis_value' }}"] = result.decode() if result else None{% endif %}
finally:
    await redis_client.close()
""",
            input_schema={"datastore_name": "str", "key": "str"},
            output_schema={"redis_value": "str"},
        )

        redis_set_template = BaseTemplate(
            name="io/redis_set",
            template_code="""
# Redis SET operation
import redis.asyncio as redis
redis_client = redis.from_url("redis://{{ params.datastore_name }}.{namespace}.svc.cluster.local:6379")
try:
    await redis_client.set(
        "{{ params.key }}",
        "{{ params.value }}"{% if params.ttl %},
        ex={{ params.ttl }}{% endif %}
    )
    {% if output_schema %}{{ context_var }}["{{ params.output or 'redis_result' }}"] = "OK"{% endif %}
finally:
    await redis_client.close()
""",
            input_schema={"datastore_name": "str", "key": "str", "value": "str"},
            output_schema={"redis_result": "str"},
        )

        # Database write template
        db_write_template = BaseTemplate(
            name="io/postgres_write",
            template_code="""
# Database write operation
async with get_db_connection("{{ params.datastore_name }}") as conn:
    {% if params.query_params %}
    result = await conn.fetchrow("{{ params.query }}", {{ params.query_params|join(', ') }})
    {% else %}
    result = await conn.execute("{{ params.query }}")
    {% endif %}
    {% if output_schema %}{{ context_var }}["{{ params.output or 'write_result' }}"] = dict(result) if result else None{% endif %}
""",
            input_schema={"datastore_name": "str", "query": "str"},
            output_schema={"write_result": "dict"},
        )

        # Conditional branch template
        conditional_template = BaseTemplate(
            name="control_flow/conditional_branch",
            template_code="""
# Conditional execution
if {{ params.condition }}:
    {% for step in params.if_true %}
    # Execute if_true step: {{ step.name }}
    # (This would be expanded with the actual step template)
    {% endfor %}
{% if params.if_false %}
else:
    {% for step in params.if_false %}
    # Execute if_false step: {{ step.name }}
    # (This would be expanded with the actual step template)
    {% endfor %}
{% endif %}
""",
            input_schema={"condition": "str", "if_true": "list", "if_false": "list"},
        )

        # Parallel execution template
        parallel_template = BaseTemplate(
            name="control_flow/parallel_execution",
            template_code="""
# Parallel execution
import asyncio

async def execute_branch_{{ loop.index }}():
    {% for branch in params.branches %}
    # Branch: {{ branch.name }}
    # (This would be expanded with the actual branch template)
    {% endfor %}

# Execute all branches in parallel
branch_tasks = [
    {% for branch in params.branches %}
    execute_branch_{{ loop.index }}(),
    {% endfor %}
]
branch_results = await asyncio.gather(*branch_tasks)
""",
            input_schema={"branches": "list"},
            output_schema={"branch_results": "list"},
        )

        # Custom function call template
        custom_function_template = BaseTemplate(
            name="logic/custom_function_call",
            template_code="""
# Custom function call
from .functions import {{ params.function_name }}

result = {{ params.function_name }}(
    {% for arg_name, arg_value in params.arguments.items() %}
    {{ arg_name }}={{ arg_value }},
    {% endfor %}
)
{% if output_schema %}{{ context_var }}["{{ params.output or 'function_result' }}"] = result{% endif %}
""",
            input_schema={"function_name": "str", "arguments": "dict"},
            output_schema={"function_result": "any"},
        )

        # Error handling template
        error_handling_template = BaseTemplate(
            name="control_flow/error_handling",
            template_code="""
# Error handling wrapper
try:
    # (Wrapped code would go here)
    pass
except {{ params.exception_type or 'Exception' }} as e:
    {% if params.on_error == 'log' %}
    logger.error(f"Error in {{ params.step_name }}: {e}")
    {% elif params.on_error == 'raise' %}
    raise HTTPException(status_code={{ params.error_code or 500 }}, detail=str(e))
    {% elif params.on_error == 'return_default' %}
    {% if output_schema %}{{ context_var }}["{{ params.output or 'result' }}"] = {{ params.default_value or 'None' }}{% endif %}
    {% endif %}
""",
            input_schema={
                "exception_type": "str",
                "on_error": "str",
                "error_code": "int",
                "default_value": "any",
            },
        )

        # Register all templates
        templates = [
            api_call_template,
            db_query_template,
            jwt_template,
            response_template,
            redis_get_template,
            redis_set_template,
            db_write_template,
            conditional_template,
            parallel_template,
            custom_function_template,
            error_handling_template,
        ]
        for template in templates:
            self._templates[template.name] = template
