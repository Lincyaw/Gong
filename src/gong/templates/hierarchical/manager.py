"""
Hierarchical template manager for intelligent template composition.
"""

from typing import Any

from pydantic import BaseModel, Field

from .metadata import TemplateLevel, TemplatePosition
from .models import TemplateContent, TemplateInstance, TemplateRequest


class FileStructure(BaseModel):
    """Represents the structure of a file to be generated."""

    path: str = Field(..., description="File path")
    primary_template: TemplateContent | None = Field(None, description="Primary file template")
    sections: dict[str, list[TemplateInstance]] = Field(
        default_factory=dict, description="Code sections with templates"
    )

    model_config = {"arbitrary_types_allowed": True}


class CompositionStep(BaseModel):
    """A step in the composition plan."""

    template_id: str = Field(..., description="Template ID")
    level: TemplateLevel = Field(..., description="Template level")
    target_file: str = Field(..., description="Target file path")
    context: dict[str, Any] = Field(..., description="Context for rendering")
    dependencies: list[str] = Field(default_factory=list, description="Dependency template IDs")
    execution_order: int = Field(default=0, description="Execution order")


class CompositionPlan(BaseModel):
    """Plan for composing multiple templates."""

    steps: list[CompositionStep] = Field(default_factory=list, description="Composition steps")

    def add_step(self, step: CompositionStep) -> None:
        """Add a step to the plan."""
        self.steps.append(step)

    def get_steps_by_level(self, level: TemplateLevel) -> list[CompositionStep]:
        """Get all steps for a specific level."""
        return [step for step in self.steps if step.level == level]


class CompositionResult(BaseModel):
    """Result of template composition."""

    files: dict[str, FileStructure] = Field(
        default_factory=dict, description="Generated file structures"
    )
    composition_plan: CompositionPlan = Field(..., description="Composition plan used")

    model_config = {"arbitrary_types_allowed": True}


class HierarchicalTemplateManager:
    """Hierarchical template manager with level-aware composition."""

    def __init__(self) -> None:
        """Initialize template manager."""
        self.templates_by_level: dict[TemplateLevel, dict[str, TemplateContent]] = {}
        self.templates_by_id: dict[str, TemplateContent] = {}

    async def register_template(self, template: TemplateContent) -> bool:
        """Register a template.

        Args:
            template: Template to register

        Returns:
            True if registration successful
        """
        level = template.metadata.scope.level

        if level not in self.templates_by_level:
            self.templates_by_level[level] = {}

        self.templates_by_level[level][template.metadata.id] = template
        self.templates_by_id[template.metadata.id] = template
        return True

    async def get_template(self, template_id: str) -> TemplateContent:
        """Get template by ID.

        Args:
            template_id: Template ID

        Returns:
            Template content

        Raises:
            KeyError: If template not found
        """
        if template_id not in self.templates_by_id:
            raise KeyError(f"Template '{template_id}' not found")
        return self.templates_by_id[template_id]

    def get_template_metadata(self, template_id: str) -> Any:
        """Get template metadata by ID.

        Args:
            template_id: Template ID

        Returns:
            Template metadata
        """
        template = self.templates_by_id.get(template_id)
        if template:
            return template.metadata
        raise KeyError(f"Template '{template_id}' not found")

    async def list_templates(self) -> list[str]:
        """List all registered template IDs.

        Returns:
            List of template IDs
        """
        return list(self.templates_by_id.keys())

    def _group_by_level(
        self, requests: list[TemplateRequest]
    ) -> dict[TemplateLevel, list[TemplateRequest]]:
        """Group template requests by level.

        Args:
            requests: List of template requests

        Returns:
            Dictionary mapping levels to requests
        """
        groups: dict[TemplateLevel, list[TemplateRequest]] = {}

        for request in requests:
            template = self.templates_by_id.get(request.template_id)
            if not template:
                continue

            level = template.metadata.scope.level

            if level not in groups:
                groups[level] = []
            groups[level].append(request)

        return groups

    def _determine_file_path(
        self, template: TemplateContent, context: dict[str, Any]
    ) -> str:
        """Determine file path for a template.

        Args:
            template: Template content
            context: Rendering context

        Returns:
            File path string
        """
        # Use position hint if available
        if template.metadata.position.file_path:
            return template.metadata.position.file_path

        # Use context if file_path is specified
        if "file_path" in context:
            return context["file_path"]

        # Default file name based on template
        service_name = context.get("service_name", "service")
        extension = template.metadata.file_extension or ".py"
        return f"{service_name}{extension}"

    def _find_target_file(
        self, template: TemplateContent, file_structure: FileStructure
    ) -> str:
        """Find target file for a template.

        Args:
            template: Template content
            file_structure: Current file structure

        Returns:
            Target file path
        """
        # If template has explicit file path, use it
        if template.metadata.position.file_path:
            return template.metadata.position.file_path

        # Otherwise, use the first available file or default
        if file_structure.path:
            return file_structure.path

        return "main.py"

    def _determine_section(self, template: TemplateContent) -> str:
        """Determine which section a template belongs to.

        Args:
            template: Template content

        Returns:
            Section name
        """
        level = template.metadata.scope.level

        if level == TemplateLevel.CLASS:
            return "classes"
        elif level in (TemplateLevel.FUNCTION, TemplateLevel.METHOD):
            return "functions"
        elif level in (TemplateLevel.BLOCK, TemplateLevel.STATEMENT, TemplateLevel.EXPRESSION):
            return "snippets"
        else:
            return "general"

    def _calculate_position(
        self, template: TemplateContent, file_info: FileStructure
    ) -> TemplatePosition:
        """Calculate position for template in file.

        Args:
            template: Template content
            file_info: File structure info

        Returns:
            Template position
        """
        return TemplatePosition(
            file_path=file_info.path,
            class_name=template.metadata.position.class_name,
            function_name=template.metadata.position.function_name,
        )

    async def compose_templates(
        self, template_requests: list[TemplateRequest]
    ) -> CompositionResult:
        """Compose multiple templates into files.

        Args:
            template_requests: List of template requests

        Returns:
            Composition result with file structures
        """
        # Group requests by level
        requests_by_level = self._group_by_level(template_requests)

        # Build file structure
        file_structures: dict[str, FileStructure] = {}

        # Process FILE level templates first to establish file structure
        if TemplateLevel.FILE in requests_by_level:
            for request in requests_by_level[TemplateLevel.FILE]:
                template = await self.get_template(request.template_id)
                file_path = self._determine_file_path(template, request.context)

                file_structures[file_path] = FileStructure(
                    path=file_path, primary_template=template, sections={}
                )

        # If no FILE level templates, create default structure
        if not file_structures:
            default_path = "main.py"
            file_structures[default_path] = FileStructure(
                path=default_path, primary_template=None, sections={}
            )

        # Process other levels
        level_order = [
            TemplateLevel.MODULE,
            TemplateLevel.CLASS,
            TemplateLevel.FUNCTION,
            TemplateLevel.METHOD,
            TemplateLevel.BLOCK,
            TemplateLevel.STATEMENT,
            TemplateLevel.EXPRESSION,
        ]

        for level in level_order:
            if level not in requests_by_level:
                continue

            for request in requests_by_level[level]:
                template = await self.get_template(request.template_id)

                # Find target file
                target_file = list(file_structures.keys())[0]  # Use first file for now
                file_info = file_structures[target_file]

                # Determine section
                section = self._determine_section(template)

                if section not in file_info.sections:
                    file_info.sections[section] = []

                # Create template instance
                position = self._calculate_position(template, file_info)
                instance = TemplateInstance(
                    template=template,
                    context=request.context,
                    position=position,
                    rendered_code=None,  # Will be rendered later
                )

                file_info.sections[section].append(instance)

        # Create composition plan
        plan = CompositionPlan()
        for request in template_requests:
            template = await self.get_template(request.template_id)
            step = CompositionStep(
                template_id=request.template_id,
                level=template.metadata.scope.level,
                target_file=list(file_structures.keys())[0],
                context=request.context,
            )
            plan.add_step(step)

        return CompositionResult(files=file_structures, composition_plan=plan)
