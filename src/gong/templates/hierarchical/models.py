"""
Template content and request models.
"""

from typing import Any

from jinja2 import BaseLoader, Environment
from pydantic import BaseModel, Field

from .metadata import TemplateMetadata, TemplatePosition


class TemplateContent(BaseModel):
    """A complete template definition with metadata and code."""

    metadata: TemplateMetadata = Field(..., description="Template metadata")
    template_code: str = Field(..., description="Jinja2 template string")
    helper_functions: dict[str, str] = Field(
        default_factory=dict, description="Helper functions code"
    )

    model_config = {"arbitrary_types_allowed": True}

    def render(self, context: dict[str, Any]) -> str:
        """Render template with given context.

        Args:
            context: Variables to use in template rendering

        Returns:
            Rendered code string
        """
        env = Environment(loader=BaseLoader())
        template = env.from_string(self.template_code)
        return template.render(**context)


class TemplateRequest(BaseModel):
    """Request to use a template in code generation."""

    template_id: str = Field(..., description="Template ID to use")
    context: dict[str, Any] = Field(..., description="Context variables for rendering")
    position_hint: TemplatePosition | None = Field(
        None, description="Position hint for where to place this template"
    )


class TemplateInstance(BaseModel):
    """An instance of a template with rendered code."""

    template: TemplateContent = Field(..., description="Original template")
    context: dict[str, Any] = Field(..., description="Context used for rendering")
    position: TemplatePosition = Field(..., description="Position in final code")
    rendered_code: str | None = Field(None, description="Rendered code")

    model_config = {"arbitrary_types_allowed": True}
