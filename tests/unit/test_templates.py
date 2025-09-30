"""
Unit tests for template system.
"""

import pytest

from gong.templates.base import BaseTemplate, InMemoryTemplateRegistry


class TestBaseTemplate:
    """Test BaseTemplate class."""

    def test_create_template(self):
        """Test creating a basic template."""
        template = BaseTemplate(
            name="test/template",
            template_code="print('Hello {{ name }}')",
            input_schema={"name": "str"},
            output_schema={"result": "str"},
        )

        assert template.name == "test/template"
        assert template.input_schema == {"name": "str"}
        assert template.output_schema == {"result": "str"}

    def test_render_template(self):
        """Test rendering a template."""
        template = BaseTemplate(
            name="test/greeting", template_code="Hello {{ name }}!", input_schema={"name": "str"}
        )

        result = template.render({"name": "World"})
        assert "Hello World!" in result

    def test_render_with_context(self):
        """Test rendering with context variable."""
        template = BaseTemplate(
            name="test/context", template_code="result = {{ value }}", input_schema={"value": "str"}
        )

        result = template.render({"value": "test"}, "my_var")
        assert "result = test" in result


class TestInMemoryTemplateRegistry:
    """Test InMemoryTemplateRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a template registry for testing."""
        return InMemoryTemplateRegistry()

    @pytest.fixture
    def sample_template(self):
        """Create a sample template for testing."""
        return BaseTemplate(
            name="test/sample",
            template_code="# Sample template\nprint('{{ message }}')",
            input_schema={"message": "str"},
        )

    async def test_register_template(self, registry, sample_template):
        """Test registering a template."""
        await registry.register_template(sample_template)

        templates = await registry.list_templates()
        assert "test/sample" in templates

    async def test_get_template(self, registry, sample_template):
        """Test getting a registered template."""
        await registry.register_template(sample_template)

        retrieved = await registry.get_template("test/sample")
        assert retrieved.name == "test/sample"
        assert retrieved.input_schema == {"message": "str"}

    async def test_get_nonexistent_template(self, registry):
        """Test getting a non-existent template."""
        with pytest.raises(KeyError):
            await registry.get_template("nonexistent/template")

    async def test_list_templates(self, registry):
        """Test listing templates."""
        # Initially should have built-in templates
        templates = await registry.list_templates()
        assert len(templates) > 0

        # Should include built-in templates
        assert "io/http_api_call" in templates
        assert "control_flow/return_response" in templates

    async def test_builtin_templates(self, registry):
        """Test that built-in templates are available."""
        # Test HTTP API call template
        http_template = await registry.get_template("io/http_api_call")
        assert http_template.name == "io/http_api_call"
        assert "target_service" in http_template.input_schema

        # Test return response template
        return_template = await registry.get_template("control_flow/return_response")
        assert return_template.name == "control_flow/return_response"
        assert "status_code" in return_template.input_schema

    async def test_template_rendering_integration(self, registry):
        """Test end-to-end template rendering."""
        http_template = await registry.get_template("io/http_api_call")

        params = {"target_service": "user-service", "path": "/v1/users/123", "method": "GET"}

        code = http_template.render(params)

        # Should contain the service name and path
        assert "user-service" in code
        assert "/v1/users/123" in code
        assert "httpx.AsyncClient" in code
