# Template Management System

This directory contains the template management systems for Gong's code generation.

## Directory Structure

```
templates/
├── base.py                 # Legacy template system (backward compatible)
├── loader.py              # Template loader utilities
├── registry.py            # File-based template registry
├── hierarchical/          # NEW: Hierarchical template management system
│   ├── __init__.py       # Public API exports
│   ├── metadata.py       # Template metadata definitions
│   ├── models.py         # Template content and request models
│   ├── manager.py        # Hierarchical template manager
│   └── optimizer.py      # Template optimizer
└── files/                 # Template files (Jinja2)
    ├── service/
    └── snippets/
```

## Systems Overview

### Legacy System (base.py, registry.py, loader.py)

The original template system based on simple Jinja2 templates. Still available for backward compatibility.

**Key features:**
- Simple template rendering
- Basic registry
- File-based template loading

**Usage:**
```python
from gong.templates.base import InMemoryTemplateRegistry

registry = InMemoryTemplateRegistry()
template = await registry.get_template("io/http_api_call")
code = template.render({"target_service": "user-service"})
```

### Hierarchical System (hierarchical/)

**NEW:** Complete rewrite with advanced features for intelligent code generation.

**Key features:**
- Multi-level templates (FILE, CLASS, FUNCTION, BLOCK, etc.)
- Metadata-driven composition
- Automatic import optimization
- Intelligent code organization
- Position-aware injection
- Comprehensive testing

**Usage:**
```python
from gong.templates.hierarchical import (
    HierarchicalTemplateManager,
    TemplateContent,
    TemplateMetadata,
    TemplateScope,
    TemplateLevel,
    CompositionStrategy,
    TemplateRequest,
    TemplateOptimizer,
)

# Create manager
manager = HierarchicalTemplateManager()

# Define templates
file_template = TemplateContent(
    metadata=TemplateMetadata(
        id="file/service",
        name="Service File",
        scope=TemplateScope(
            level=TemplateLevel.FILE,
            composition_strategy=CompositionStrategy.MERGE
        ),
    ),
    template_code="...",
)

# Register and compose
await manager.register_template(file_template)
result = await manager.compose_templates([
    TemplateRequest(template_id="file/service", context={...})
])

# Optimize
optimizer = TemplateOptimizer(manager)
optimized = await optimizer.optimize_by_levels(
    result.composition_plan,
    result.files
)
```

## When to Use Which System?

### Use Legacy System When:
- Working with existing code that uses it
- Need simple template rendering
- Backward compatibility is required

### Use Hierarchical System When:
- Generating complex multi-file services
- Need intelligent code composition
- Want automatic import optimization
- Require metadata-driven templates
- Building new features

## Documentation

- **Hierarchical System**: See [docs/hierarchical_templates.md](../../docs/hierarchical_templates.md)
- **Examples**: See [examples/hierarchical_templates_example.py](../../examples/hierarchical_templates_example.py)

## Testing

```bash
# Test legacy system
uv run pytest tests/test_templates.py -v

# Test hierarchical system
uv run pytest tests/test_hierarchical_templates.py -v

# Test all
uv run pytest tests/test_*templates*.py -v
```

## Migration Path

The hierarchical system is designed to coexist with the legacy system. Migration is gradual:

1. **Phase 1** (Current): Both systems available
2. **Phase 2**: New features use hierarchical system only
3. **Phase 3**: Migrate existing templates to hierarchical system
4. **Phase 4**: Deprecate legacy system (future)

## Contributing

When adding new templates:

1. **For simple templates**: Add to legacy system
2. **For complex multi-level templates**: Use hierarchical system
3. **Include tests**: Add tests for all new templates
4. **Document metadata**: Use comprehensive metadata in hierarchical templates
5. **Follow naming**: Use `category/template_name` format for IDs

## Key Concepts

### Template Levels

Templates are organized by granularity:

- **FILE**: Complete file (e.g., entire service.py)
- **MODULE**: Group of related classes/functions
- **CLASS**: Class definition
- **FUNCTION**: Function or method
- **BLOCK**: Code block (if-else, try-catch)
- **STATEMENT**: Single statement
- **EXPRESSION**: Expression

### Composition Strategies

How templates combine:

- **MERGE**: Combine into same file
- **INJECT**: Insert at injection point
- **WRAP**: Wrap existing code
- **EXTEND**: Inheritance
- **SEPARATE_FILES**: Generate separate files

### Import Optimization

The hierarchical system automatically:

- Deduplicates imports
- Merges imports from same module
- Sorts imports (standard library first, then third-party)
- Organizes import statements

## Support

For questions or issues:

- Check documentation: `docs/hierarchical_templates.md`
- Run examples: `examples/hierarchical_templates_example.py`
- Review tests: `tests/test_hierarchical_templates.py`
