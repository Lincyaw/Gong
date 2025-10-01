"""
Unit tests for hierarchical template management system.
"""

import pytest

from gong.templates.hierarchical import (
    CompositionStrategy,
    HierarchicalTemplateManager,
    ImportDependency,
    TemplateContent,
    TemplateLevel,
    TemplateMetadata,
    TemplateOptimizer,
    TemplatePosition,
    TemplateRequest,
    TemplateScope,
    Variable,
)


@pytest.fixture
def template_manager():
    """Create a template manager for testing."""
    return HierarchicalTemplateManager()


@pytest.fixture
def sample_file_template():
    """Create a sample file-level template."""
    return TemplateContent(
        metadata=TemplateMetadata(
            id="file/fastapi_service",
            name="FastAPI Service File",
            description="Complete FastAPI service file",
            scope=TemplateScope(level=TemplateLevel.FILE, composition_strategy=CompositionStrategy.MERGE),
            file_extension=".py",
            generates_classes=["ServiceApp"],
            import_dependencies=[
                ImportDependency(module="fastapi", imports=["FastAPI", "HTTPException"]),
                ImportDependency(module="uvicorn", imports=[]),
            ],
        ),
        template_code="""
# FastAPI Service: {{ service_name }}
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="{{ service_name }}")

{{ inject_endpoints }}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
""",
    )


@pytest.fixture
def sample_function_template():
    """Create a sample function-level template."""
    return TemplateContent(
        metadata=TemplateMetadata(
            id="function/api_endpoint",
            name="API Endpoint Function",
            description="FastAPI endpoint function",
            scope=TemplateScope(
                level=TemplateLevel.FUNCTION,
                composition_strategy=CompositionStrategy.INJECT,
                target_injection_point="inject_endpoints",
            ),
            generates_functions=["{{ endpoint_name }}"],
            inputs=[
                Variable(name="endpoint_name", type="str", description="Endpoint function name"),
                Variable(name="path", type="str", description="API path"),
                Variable(name="method", type="str", description="HTTP method"),
            ],
            outputs=[Variable(name="response", type="dict", description="Response data")],
        ),
        template_code="""
@app.{{ method }}("{{ path }}")
async def {{ endpoint_name }}():
    \"\"\"{{ description | default('API endpoint') }}\"\"\"
    return {"status": "success"}
""",
    )


@pytest.fixture
def sample_block_template():
    """Create a sample block-level template."""
    return TemplateContent(
        metadata=TemplateMetadata(
            id="block/error_handling",
            name="Error Handling Block",
            description="Try-except error handling",
            scope=TemplateScope(level=TemplateLevel.BLOCK, composition_strategy=CompositionStrategy.WRAP),
            import_dependencies=[
                ImportDependency(module="logging", imports=[], is_standard_library=True)
            ],
        ),
        template_code="""
try:
    {{ wrapped_code }}
except Exception as e:
    logger.error(f"Error: {e}")
    raise
""",
    )


@pytest.mark.asyncio
async def test_template_registration(template_manager, sample_file_template):
    """Test registering a template."""
    result = await template_manager.register_template(sample_file_template)
    assert result is True

    # Verify template can be retrieved
    retrieved = await template_manager.get_template("file/fastapi_service")
    assert retrieved.metadata.id == "file/fastapi_service"
    assert retrieved.metadata.scope.level == TemplateLevel.FILE


@pytest.mark.asyncio
async def test_template_listing(template_manager, sample_file_template, sample_function_template):
    """Test listing templates."""
    await template_manager.register_template(sample_file_template)
    await template_manager.register_template(sample_function_template)

    templates = await template_manager.list_templates()
    assert len(templates) == 2
    assert "file/fastapi_service" in templates
    assert "function/api_endpoint" in templates


@pytest.mark.asyncio
async def test_template_not_found(template_manager):
    """Test error handling for missing template."""
    with pytest.raises(KeyError) as exc_info:
        await template_manager.get_template("nonexistent/template")

    assert "nonexistent/template" in str(exc_info.value)


@pytest.mark.asyncio
async def test_simple_template_composition(template_manager, sample_file_template):
    """Test composing a single file template."""
    await template_manager.register_template(sample_file_template)

    requests = [
        TemplateRequest(template_id="file/fastapi_service", context={"service_name": "UserService"})
    ]

    result = await template_manager.compose_templates(requests)

    assert len(result.files) >= 1
    assert result.composition_plan is not None
    assert len(result.composition_plan.steps) == 1


@pytest.mark.asyncio
async def test_multi_level_composition(
    template_manager, sample_file_template, sample_function_template
):
    """Test composing templates at different levels."""
    await template_manager.register_template(sample_file_template)
    await template_manager.register_template(sample_function_template)

    requests = [
        TemplateRequest(template_id="file/fastapi_service", context={"service_name": "UserService"}),
        TemplateRequest(
            template_id="function/api_endpoint",
            context={"endpoint_name": "get_user", "path": "/users/{user_id}", "method": "get"},
        ),
    ]

    result = await template_manager.compose_templates(requests)

    assert len(result.files) >= 1
    assert len(result.composition_plan.steps) == 2

    # Verify both levels are present
    levels = [step.level for step in result.composition_plan.steps]
    assert TemplateLevel.FILE in levels
    assert TemplateLevel.FUNCTION in levels


@pytest.mark.asyncio
async def test_template_rendering(sample_function_template):
    """Test rendering a template with context."""
    context = {
        "endpoint_name": "get_users",
        "path": "/users",
        "method": "get",
        "description": "Get all users",
    }

    rendered = sample_function_template.render(context)

    assert "get_users" in rendered
    assert "/users" in rendered
    assert "@app.get" in rendered
    assert "Get all users" in rendered


def test_import_dependency_equality():
    """Test ImportDependency equality and hashing."""
    dep1 = ImportDependency(module="fastapi", imports=["FastAPI", "HTTPException"])
    dep2 = ImportDependency(module="fastapi", imports=["HTTPException", "FastAPI"])
    dep3 = ImportDependency(module="uvicorn", imports=[])

    # Should be equal even with different order
    assert dep1 == dep2
    assert dep1 != dep3

    # Should be hashable for use in sets
    deps_set = {dep1, dep2, dep3}
    assert len(deps_set) == 2  # dep1 and dep2 are the same


@pytest.mark.asyncio
async def test_import_optimization(template_manager, sample_file_template, sample_block_template):
    """Test import optimization and deduplication."""
    await template_manager.register_template(sample_file_template)
    await template_manager.register_template(sample_block_template)

    requests = [
        TemplateRequest(template_id="file/fastapi_service", context={"service_name": "UserService"}),
        TemplateRequest(template_id="block/error_handling", context={"wrapped_code": "pass"}),
    ]

    result = await template_manager.compose_templates(requests)
    optimizer = TemplateOptimizer(template_manager)

    optimized = await optimizer.optimize_by_levels(result.composition_plan, result.files)

    assert len(optimized.files) >= 1

    # Check that imports are present and optimized
    file_path = list(optimized.files.keys())[0]
    optimized_file = optimized.files[file_path]

    assert optimized_file.code
    assert len(optimized_file.imports) > 0


@pytest.mark.asyncio
async def test_template_metadata_validation():
    """Test template metadata validation."""
    metadata = TemplateMetadata(
        id="test/template",
        name="Test Template",
        scope=TemplateScope(level=TemplateLevel.FUNCTION, composition_strategy=CompositionStrategy.INJECT),
        inputs=[Variable(name="param1", type="str"), Variable(name="param2", type="int", required=False)],
        outputs=[Variable(name="result", type="dict")],
        import_dependencies=[ImportDependency(module="typing", imports=["Dict", "Any"], is_standard_library=True)],
    )

    # Verify all fields are accessible
    assert metadata.id == "test/template"
    assert metadata.scope.level == TemplateLevel.FUNCTION
    assert len(metadata.inputs) == 2
    assert len(metadata.outputs) == 1
    assert len(metadata.import_dependencies) == 1


@pytest.mark.asyncio
async def test_composition_with_position_hints(template_manager, sample_function_template):
    """Test composition with position hints."""
    await template_manager.register_template(sample_function_template)

    position_hint = TemplatePosition(file_path="custom_service.py", class_name="ServiceApp")

    requests = [
        TemplateRequest(
            template_id="function/api_endpoint",
            context={"endpoint_name": "create_user", "path": "/users", "method": "post"},
            position_hint=position_hint,
        )
    ]

    result = await template_manager.compose_templates(requests)

    # Verify composition completed
    assert result.files
    assert result.composition_plan.steps


@pytest.mark.asyncio
async def test_level_priority_ordering(template_manager):
    """Test that templates are processed in correct level priority order."""
    optimizer = TemplateOptimizer(template_manager)

    # Verify level priorities
    assert optimizer._get_level_priority(TemplateLevel.FILE) < optimizer._get_level_priority(
        TemplateLevel.CLASS
    )
    assert optimizer._get_level_priority(TemplateLevel.CLASS) < optimizer._get_level_priority(
        TemplateLevel.FUNCTION
    )
    assert optimizer._get_level_priority(TemplateLevel.FUNCTION) < optimizer._get_level_priority(
        TemplateLevel.BLOCK
    )


@pytest.mark.asyncio
async def test_complete_service_generation(
    template_manager, sample_file_template, sample_function_template
):
    """Test complete service code generation from multiple templates."""
    # Register templates
    await template_manager.register_template(sample_file_template)
    await template_manager.register_template(sample_function_template)

    # Create requests for a complete service
    requests = [
        TemplateRequest(
            template_id="file/fastapi_service", context={"service_name": "ProductService"}
        ),
        TemplateRequest(
            template_id="function/api_endpoint",
            context={
                "endpoint_name": "list_products",
                "path": "/products",
                "method": "get",
                "description": "List all products",
            },
        ),
        TemplateRequest(
            template_id="function/api_endpoint",
            context={
                "endpoint_name": "get_product",
                "path": "/products/{product_id}",
                "method": "get",
                "description": "Get product by ID",
            },
        ),
    ]

    # Compose templates
    result = await template_manager.compose_templates(requests)

    # Optimize
    optimizer = TemplateOptimizer(template_manager)
    optimized = await optimizer.optimize_by_levels(result.composition_plan, result.files)

    # Verify result
    assert len(optimized.files) >= 1
    file_path = list(optimized.files.keys())[0]
    optimized_file = optimized.files[file_path]

    # Check generated code contains expected elements
    assert "ProductService" in optimized_file.code
    assert "FastAPI" in optimized_file.code or "fastapi" in optimized_file.code.lower()


@pytest.mark.asyncio
async def test_helper_functions():
    """Test template with helper functions."""
    template = TemplateContent(
        metadata=TemplateMetadata(
            id="test/with_helpers",
            name="Template with Helpers",
            scope=TemplateScope(level=TemplateLevel.FUNCTION, composition_strategy=CompositionStrategy.INJECT),
        ),
        template_code="""
def main_function():
    result = helper_function()
    return result
""",
        helper_functions={
            "helper_function": """
def helper_function():
    return "helper result"
"""
        },
    )

    # Verify helper functions are stored
    assert len(template.helper_functions) == 1
    assert "helper_function" in template.helper_functions


@pytest.mark.asyncio
async def test_template_dependencies(template_manager):
    """Test template dependency tracking."""
    base_template = TemplateContent(
        metadata=TemplateMetadata(
            id="base/function",
            name="Base Function",
            scope=TemplateScope(level=TemplateLevel.FUNCTION, composition_strategy=CompositionStrategy.INJECT),
        ),
        template_code="def base(): pass",
    )

    dependent_template = TemplateContent(
        metadata=TemplateMetadata(
            id="dependent/function",
            name="Dependent Function",
            scope=TemplateScope(level=TemplateLevel.FUNCTION, composition_strategy=CompositionStrategy.INJECT),
            template_dependencies=["base/function"],
        ),
        template_code="def dependent(): base()",
    )

    await template_manager.register_template(base_template)
    await template_manager.register_template(dependent_template)

    # Verify dependency is recorded
    dependent = await template_manager.get_template("dependent/function")
    assert "base/function" in dependent.metadata.template_dependencies


@pytest.mark.asyncio
async def test_optimization_log(template_manager, sample_file_template, sample_function_template):
    """Test that optimization process generates logs."""
    await template_manager.register_template(sample_file_template)
    await template_manager.register_template(sample_function_template)

    requests = [
        TemplateRequest(template_id="file/fastapi_service", context={"service_name": "TestService"}),
        TemplateRequest(
            template_id="function/api_endpoint",
            context={"endpoint_name": "test_endpoint", "path": "/test", "method": "get"},
        ),
    ]

    result = await template_manager.compose_templates(requests)
    optimizer = TemplateOptimizer(template_manager)
    optimized = await optimizer.optimize_by_levels(result.composition_plan, result.files)

    # Verify optimization logs are generated
    assert len(optimized.optimization_log) > 0
    assert any("Optimized" in log for log in optimized.optimization_log)
