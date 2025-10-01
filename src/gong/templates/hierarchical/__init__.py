"""
Hierarchical template management system.

This module provides a complete rewrite of the template management system
with support for multi-level templates, intelligent composition, and optimization.
"""

from .manager import HierarchicalTemplateManager
from .metadata import (
    CompositionStrategy,
    ImportDependency,
    TemplateLevel,
    TemplateMetadata,
    TemplatePosition,
    TemplateScope,
    Variable,
)
from .models import TemplateContent, TemplateRequest
from .optimizer import OptimizedComposition, TemplateOptimizer

__all__ = [
    # Enums
    "TemplateLevel",
    "CompositionStrategy",
    # Data structures
    "Variable",
    "ImportDependency",
    "TemplateScope",
    "TemplatePosition",
    "TemplateMetadata",
    "TemplateContent",
    "TemplateRequest",
    # Core classes
    "HierarchicalTemplateManager",
    "TemplateOptimizer",
    "OptimizedComposition",
]
