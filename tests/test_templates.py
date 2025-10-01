"""
Tests for template system.
"""

import pytest

from gong.templates.base import BaseTemplate, InMemoryTemplateRegistry


@pytest.fixture
def template_registry():
    """Create a template registry for testing."""
    return InMemoryTemplateRegistry()


def test_base_template_creation():
    """Test BaseTemplate creation and rendering."""
    template = BaseTemplate(
        name="test/template",
        template_code="Hello {{ params.name }}!",
        input_schema={"name": "str"},
        output_schema={"greeting": "str"},
    )

    assert template.name == "test/template"
    assert template.input_schema == {"name": "str"}
    assert template.output_schema == {"greeting": "str"}

    # Test rendering
    result = template.render({"name": "World"})
    assert "Hello World!" in result


@pytest.mark.asyncio
async def test_template_registry(template_registry):
    """Test template registry operations."""
    # Test listing templates (should have built-in templates)
    templates = await template_registry.list_templates()
    assert len(templates) > 0
    assert "io/http_api_call" in templates

    # Test getting a template
    template = await template_registry.get_template("io/http_api_call")
    assert template.name == "io/http_api_call"

    # Test registering a new template
    new_template = BaseTemplate(
        name="test/custom", template_code="Custom template", input_schema={}
    )
    await template_registry.register_template(new_template)

    templates = await template_registry.list_templates()
    assert "test/custom" in templates


@pytest.mark.asyncio
async def test_template_not_found(template_registry):
    """Test template not found error."""
    with pytest.raises(KeyError) as exc_info:
        await template_registry.get_template("nonexistent/template")

    assert "nonexistent/template" in str(exc_info.value)
