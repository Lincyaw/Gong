"""
Template metadata and type definitions for hierarchical template system.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TemplateLevel(str, Enum):
    """Template level enumeration - defines the granularity of code generation."""

    # File level
    FILE = "file"  # Complete file template (e.g., entire service file)
    MODULE = "module"  # Module level (group of related classes and functions)
    CLASS = "class"  # Class level template

    # Function level
    FUNCTION = "function"  # Complete function template
    METHOD = "method"  # Class method template

    # Code snippet level
    BLOCK = "block"  # Code block (e.g., if-else, try-catch)
    STATEMENT = "statement"  # Statement level (e.g., single line assignment)
    EXPRESSION = "expression"  # Expression level (e.g., variable operation)

    # Configuration level
    CONFIGURATION = "configuration"  # Configuration file template
    DEPLOYMENT = "deployment"  # Deployment configuration template


class CompositionStrategy(str, Enum):
    """Composition strategy enumeration - how templates combine."""

    MERGE = "merge"  # Merge into the same file
    SEPARATE_FILES = "separate_files"  # Generate independent files
    INJECT = "inject"  # Inject into specified location
    WRAP = "wrap"  # Wrap existing code
    EXTEND = "extend"  # Inheritance extension


class Variable(BaseModel):
    """Variable definition for template inputs/outputs."""

    name: str = Field(..., description="Variable name")
    type: str = Field(..., description="Variable type (e.g., 'str', 'int', 'dict')")
    description: str | None = Field(None, description="Variable description")
    required: bool = Field(default=True, description="Whether variable is required")
    default: Any = Field(default=None, description="Default value if not required")


class ImportDependency(BaseModel):
    """Import dependency definition."""

    module: str = Field(..., description="Module to import (e.g., 'httpx', 'fastapi')")
    imports: list[str] = Field(
        default_factory=list, description="Specific imports (e.g., ['FastAPI', 'HTTPException'])"
    )
    alias: str | None = Field(None, description="Import alias (e.g., 'pd' for pandas)")
    is_standard_library: bool = Field(
        default=False, description="Whether this is a standard library import"
    )

    def __hash__(self) -> int:
        """Make ImportDependency hashable for use in sets."""
        return hash((self.module, tuple(sorted(self.imports)), self.alias))

    def __eq__(self, other: object) -> bool:
        """Check equality for deduplication."""
        if not isinstance(other, ImportDependency):
            return False
        return (
            self.module == other.module
            and sorted(self.imports) == sorted(other.imports)
            and self.alias == other.alias
        )


class TemplateScope(BaseModel):
    """Template scope definition."""

    level: TemplateLevel = Field(..., description="Template level")
    composition_strategy: CompositionStrategy = Field(..., description="How this template composes")
    target_injection_point: str | None = Field(
        None, description="Target injection point when using INJECT strategy"
    )
    merge_priority: int = Field(
        default=100, description="Merge priority, lower numbers = higher priority"
    )


class TemplatePosition(BaseModel):
    """Template position information in generated code."""

    file_path: str | None = Field(None, description="Target file path")
    class_name: str | None = Field(None, description="Parent class name")
    function_name: str | None = Field(None, description="Parent function name")
    line_number: int | None = Field(None, description="Line number position")
    insertion_point: str | None = Field(None, description="Insertion point identifier")


class TemplateMetadata(BaseModel):
    """Complete metadata description for a template."""

    # Basic information
    id: str = Field(..., description="Unique template ID (e.g., 'io/http_api_call')")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(default="", description="Template description")
    version: str = Field(default="1.0.0", description="Template version (semver)")
    category: str = Field(default="general", description="Template category")

    # Scope and composition
    scope: TemplateScope = Field(..., description="Template scope and composition strategy")
    position: TemplatePosition = Field(
        default_factory=TemplatePosition, description="Position information"
    )

    # Interface definition
    inputs: list[Variable] = Field(
        default_factory=list, description="Input variables required by template"
    )
    outputs: list[Variable] = Field(
        default_factory=list, description="Output variables produced by template"
    )

    # Dependencies
    import_dependencies: list[ImportDependency] = Field(
        default_factory=list, description="Python packages to import"
    )
    template_dependencies: list[str] = Field(
        default_factory=list, description="Other template IDs this depends on"
    )

    # Code structure information
    generates_imports: bool = Field(
        default=False, description="Whether this template generates import statements"
    )
    generates_classes: list[str] = Field(
        default_factory=list, description="List of class names this template generates"
    )
    generates_functions: list[str] = Field(
        default_factory=list, description="List of function names this template generates"
    )
    modifies_existing: bool = Field(
        default=False, description="Whether this modifies existing code"
    )

    # File-level specific attributes
    file_extension: str | None = Field(None, description="Generated file extension (e.g., '.py')")

    # Snippet-level specific attributes
    injection_points: dict[str, str] = Field(
        default_factory=dict, description="Injection points this template provides"
    )
    code_context_required: list[str] = Field(
        default_factory=list, description="Required code context for this template"
    )

    # Composition constraints
    compatible_levels: list[TemplateLevel] = Field(
        default_factory=list, description="Compatible template levels for composition"
    )
    composition_constraints: dict[str, Any] = Field(
        default_factory=dict, description="Composition constraints"
    )

    # Tags and metadata
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
