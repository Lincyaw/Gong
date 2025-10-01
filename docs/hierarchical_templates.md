# Hierarchical Template Management System

## Overview

The Hierarchical Template Management System is a complete rewrite of the template management functionality in Gong. It provides intelligent code generation through multi-level templates, automated composition, and optimization.

## Key Features

- **Multi-Level Templates**: Support for templates at different granularities (FILE, MODULE, CLASS, FUNCTION, BLOCK, STATEMENT, EXPRESSION)
- **Intelligent Composition**: Automatic composition of templates based on their levels and strategies
- **Import Optimization**: Automatic deduplication and optimization of import statements
- **Metadata-Driven**: Rich metadata for each template defining inputs, outputs, dependencies, and more
- **Position-Aware**: Precise control over where code is injected
- **Extensible**: Easy to add new templates and composition strategies

## Architecture

### Core Components

1. **TemplateMetadata**: Complete metadata description for templates
2. **TemplateContent**: Template definition with code and metadata
3. **HierarchicalTemplateManager**: Manager for registering and composing templates
4. **TemplateOptimizer**: Optimizer for intelligent code generation and optimization

### Template Levels

Templates are organized into different levels based on their granularity:

```python
class TemplateLevel(str, Enum):
    FILE = "file"                    # Complete file template
    MODULE = "module"                # Module level
    CLASS = "class"                  # Class level template
    FUNCTION = "function"            # Complete function template
    METHOD = "method"                # Class method template
    BLOCK = "block"                  # Code block (if-else, try-catch)
    STATEMENT = "statement"          # Statement level
    EXPRESSION = "expression"        # Expression level
    CONFIGURATION = "configuration"  # Configuration file
    DEPLOYMENT = "deployment"        # Deployment configuration
```

### Composition Strategies

Each template can define how it composes with others:

```python
class CompositionStrategy(str, Enum):
    MERGE = "merge"              # Merge into the same file
    SEPARATE_FILES = "separate_files"  # Generate independent files
    INJECT = "inject"            # Inject into specified location
    WRAP = "wrap"                # Wrap existing code
    EXTEND = "extend"            # Inheritance extension
```

## Usage

### Basic Example

```python
import asyncio
from gong.templates.hierarchical import (
    HierarchicalTemplateManager,
    TemplateContent,
    TemplateMetadata,
    TemplateScope,
    TemplateLevel,
    CompositionStrategy,
    TemplateRequest,
    TemplateOptimizer,
    ImportDependency,
)

async def main():
    # Create template manager
    manager = HierarchicalTemplateManager()
    
    # Define a file-level template
    file_template = TemplateContent(
        metadata=TemplateMetadata(
            id="file/fastapi_service",
            name="FastAPI Service",
            scope=TemplateScope(
                level=TemplateLevel.FILE,
                composition_strategy=CompositionStrategy.MERGE
            ),
            import_dependencies=[
                ImportDependency(module="fastapi", imports=["FastAPI"])
            ],
        ),
        template_code=\"\"\"
app = FastAPI(title="{{ service_name }}")

{{ inject_endpoints }}
\"\"\",
    )
    
    # Define a function-level template
    function_template = TemplateContent(
        metadata=TemplateMetadata(
            id="function/api_endpoint",
            name="API Endpoint",
            scope=TemplateScope(
                level=TemplateLevel.FUNCTION,
                composition_strategy=CompositionStrategy.INJECT,
                target_injection_point="inject_endpoints"
            ),
        ),
        template_code=\"\"\"
@app.{{ method }}("{{ path }}")
async def {{ endpoint_name }}():
    return {"status": "success"}
\"\"\",
    )
    
    # Register templates
    await manager.register_template(file_template)
    await manager.register_template(function_template)
    
    # Create composition requests
    requests = [
        TemplateRequest(
            template_id="file/fastapi_service",
            context={"service_name": "MyService"}
        ),
        TemplateRequest(
            template_id="function/api_endpoint",
            context={
                "endpoint_name": "get_users",
                "path": "/users",
                "method": "get"
            }
        ),
    ]
    
    # Compose and optimize
    result = await manager.compose_templates(requests)
    optimizer = TemplateOptimizer(manager)
    optimized = await optimizer.optimize_by_levels(
        result.composition_plan,
        result.files
    )
    
    # Get generated code
    for file_path, file_content in optimized.files.items():
        print(f"{file_path}:")
        print(file_content.code)

asyncio.run(main())
```

### Advanced Features

#### Template Dependencies

Templates can declare dependencies on other templates:

```python
TemplateMetadata(
    id="dependent/template",
    template_dependencies=["base/template"],
    # ...
)
```

#### Helper Functions

Templates can include helper functions that are generated alongside the main code:

```python
TemplateContent(
    metadata=...,
    template_code="...",
    helper_functions={
        "validate_input": \"\"\"
def validate_input(data):
    return data is not None
\"\"\"
    }
)
```

#### Position Hints

Specify where a template should be placed:

```python
TemplateRequest(
    template_id="function/my_function",
    context={...},
    position_hint=TemplatePosition(
        file_path="custom_service.py",
        class_name="ServiceHandler"
    )
)
```

## Template Metadata

Each template includes comprehensive metadata:

```python
TemplateMetadata(
    id="io/http_api_call",           # Unique identifier
    name="HTTP API Call",             # Human-readable name
    description="...",                # Description
    version="1.0.0",                  # Semantic version
    category="io",                    # Category
    
    # Scope and composition
    scope=TemplateScope(...),
    position=TemplatePosition(...),
    
    # Interface definition
    inputs=[
        Variable(name="url", type="str", required=True),
        Variable(name="method", type="str", default="GET"),
    ],
    outputs=[
        Variable(name="response", type="dict"),
    ],
    
    # Dependencies
    import_dependencies=[
        ImportDependency(module="httpx", imports=[])
    ],
    template_dependencies=["base/http"],
    
    # Code structure
    generates_classes=["HttpClient"],
    generates_functions=["make_request"],
    injection_points={"before_request": "...", "after_response": "..."},
    
    # Metadata
    tags=["http", "api", "io"],
)
```

## Testing

The system includes comprehensive unit tests covering:

- Template registration and retrieval
- Multi-level composition
- Import optimization
- Code generation
- Error handling
- Dependency tracking

Run tests with:

```bash
uv run pytest tests/test_hierarchical_templates.py -v
```

## Examples

See `examples/hierarchical_templates_example.py` for a complete working example demonstrating:

- Registration of multiple template levels
- Composition of a complete microservice
- Import optimization
- Code generation

Run the example:

```bash
uv run python examples/hierarchical_templates_example.py
```

## Benefits Over Previous System

1. **Structured Metadata**: Every template has complete metadata defining its interface, dependencies, and behavior
2. **Level-Aware Composition**: Templates compose intelligently based on their levels
3. **Automatic Optimization**: Import deduplication and code optimization happen automatically
4. **Extensible Design**: Easy to add new template types and composition strategies
5. **Type Safety**: Full type hints and Pydantic validation
6. **Better Testing**: Comprehensive test coverage with clear test cases

## Migration Guide

The hierarchical template system is a new addition and doesn't replace the existing template system immediately. Both can coexist:

- **Existing System** (`gong.templates.base`): Continue to use for backward compatibility
- **New System** (`gong.templates.hierarchical`): Use for new code and gradual migration

To migrate existing templates:

1. Create `TemplateMetadata` with appropriate level and scope
2. Wrap template code in `TemplateContent`
3. Register with `HierarchicalTemplateManager`
4. Update composition code to use `TemplateRequest`
5. Use `TemplateOptimizer` for code generation

## Future Enhancements

- **Template Validation**: Validate templates against schemas
- **Template Catalog**: Central registry of reusable templates
- **Template Versioning**: Version control for templates
- **Template Testing**: Framework for testing templates in isolation
- **Advanced Injection**: More sophisticated injection point handling
- **Code Analysis**: Static analysis of generated code
- **Template Composition Rules**: Declarative rules for composition
