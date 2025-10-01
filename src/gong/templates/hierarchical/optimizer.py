"""
Template optimizer for intelligent code combination and optimization.
"""

from typing import Any

from pydantic import BaseModel, Field

from .manager import CompositionPlan, CompositionStep, FileStructure
from .metadata import ImportDependency, TemplateLevel


class OptimizedFile(BaseModel):
    """Optimized file with final code."""

    path: str = Field(..., description="File path")
    code: str = Field(..., description="Final optimized code")
    imports: list[ImportDependency] = Field(
        default_factory=list, description="Optimized imports"
    )
    optimization_log: list[str] = Field(
        default_factory=list, description="Optimization actions taken"
    )

    model_config = {"arbitrary_types_allowed": True}


class OptimizedComposition(BaseModel):
    """Result of template optimization."""

    files: dict[str, OptimizedFile] = Field(
        default_factory=dict, description="Optimized files"
    )
    optimization_log: list[str] = Field(
        default_factory=list, description="Overall optimization log"
    )

    model_config = {"arbitrary_types_allowed": True}


class TemplateOptimizer:
    """Optimizer for template composition with level-aware optimization."""

    def __init__(self, template_manager: Any) -> None:
        """Initialize optimizer.

        Args:
            template_manager: Template manager instance
        """
        self.template_manager = template_manager

    def _get_level_priority(self, level: TemplateLevel) -> int:
        """Get priority for a template level (lower = higher priority).

        Args:
            level: Template level

        Returns:
            Priority value
        """
        priority_map = {
            TemplateLevel.FILE: 10,
            TemplateLevel.CONFIGURATION: 15,
            TemplateLevel.MODULE: 20,
            TemplateLevel.CLASS: 30,
            TemplateLevel.FUNCTION: 40,
            TemplateLevel.METHOD: 45,
            TemplateLevel.BLOCK: 50,
            TemplateLevel.STATEMENT: 60,
            TemplateLevel.EXPRESSION: 70,
        }
        return priority_map.get(level, 100)

    def _group_steps_by_file(
        self, plan: CompositionPlan
    ) -> dict[str, list[CompositionStep]]:
        """Group composition steps by target file.

        Args:
            plan: Composition plan

        Returns:
            Dictionary mapping file paths to steps
        """
        files: dict[str, list[CompositionStep]] = {}

        for step in plan.steps:
            if step.target_file not in files:
                files[step.target_file] = []
            files[step.target_file].append(step)

        return files

    def _optimize_imports(self, steps: list[CompositionStep]) -> list[ImportDependency]:
        """Optimize and deduplicate imports from multiple templates.

        Args:
            steps: Composition steps

        Returns:
            Optimized list of imports
        """
        import_map: dict[str, ImportDependency] = {}

        for step in steps:
            template = self.template_manager.templates_by_id.get(step.template_id)
            if not template:
                continue

            for import_dep in template.metadata.import_dependencies:
                if import_dep.module in import_map:
                    # Merge imports from same module
                    existing = import_map[import_dep.module]
                    merged_imports = list(set(existing.imports + import_dep.imports))
                    import_map[import_dep.module] = ImportDependency(
                        module=import_dep.module,
                        imports=merged_imports,
                        alias=import_dep.alias or existing.alias,
                        is_standard_library=import_dep.is_standard_library,
                    )
                else:
                    import_map[import_dep.module] = import_dep

        # Sort: standard library first, then third-party
        imports = list(import_map.values())
        std_imports = [imp for imp in imports if imp.is_standard_library]
        third_party = [imp for imp in imports if not imp.is_standard_library]

        return sorted(std_imports, key=lambda x: x.module) + sorted(
            third_party, key=lambda x: x.module
        )

    def _generate_import_code(self, imports: list[ImportDependency]) -> str:
        """Generate import statements code.

        Args:
            imports: List of import dependencies

        Returns:
            Import code string
        """
        lines = []

        for imp in imports:
            if imp.imports:
                # from module import X, Y
                imports_str = ", ".join(sorted(imp.imports))
                line = f"from {imp.module} import {imports_str}"
            else:
                # import module [as alias]
                line = f"import {imp.module}"
                if imp.alias:
                    line += f" as {imp.alias}"

            lines.append(line)

        return "\n".join(lines)

    async def _render_template_instances(
        self, file_structure: FileStructure
    ) -> dict[str, list[str]]:
        """Render all template instances in a file structure.

        Args:
            file_structure: File structure with template instances

        Returns:
            Dictionary mapping sections to rendered code
        """
        rendered_sections: dict[str, list[str]] = {}

        for section_name, instances in file_structure.sections.items():
            rendered_sections[section_name] = []

            for instance in instances:
                rendered = instance.template.render(instance.context)
                rendered_sections[section_name].append(rendered)

        return rendered_sections

    def _compose_file_code(
        self,
        file_structure: FileStructure,
        imports: list[ImportDependency],
        rendered_sections: dict[str, list[str]],
        primary_rendered: str | None = None,
    ) -> str:
        """Compose final file code from parts.

        Args:
            file_structure: File structure
            imports: Optimized imports
            rendered_sections: Rendered code sections
            primary_rendered: Rendered primary template (if any)

        Returns:
            Complete file code
        """
        parts = []

        # File header
        parts.append('"""')
        parts.append("Generated by Gong - Microservice Simulation Platform")
        parts.append('"""')
        parts.append("")

        # Imports
        if imports:
            import_code = self._generate_import_code(imports)
            parts.append(import_code)
            parts.append("")

        # Primary template (file-level) if exists
        if primary_rendered:
            # If primary template has injection points, replace them with rendered sections
            file_code = primary_rendered

            # Try to inject sections into injection points
            for section_name, section_codes in rendered_sections.items():
                injection_point = f"{{{{ inject_{section_name} }}}}"
                if injection_point in file_code:
                    section_content = "\n\n".join(code.strip() for code in section_codes)
                    file_code = file_code.replace(injection_point, section_content)

            # Generic injection point for all sections
            if "{{ inject_endpoints }}" in file_code:
                all_sections = []
                for section in ["classes", "functions", "snippets", "general"]:
                    if section in rendered_sections:
                        all_sections.extend(rendered_sections[section])
                section_content = "\n\n".join(code.strip() for code in all_sections)
                file_code = file_code.replace("{{ inject_endpoints }}", section_content)

            parts.append(file_code.strip())
        else:
            # No primary template, just render sections in order
            section_order = ["classes", "functions", "snippets", "general"]

            for section in section_order:
                if section in rendered_sections and rendered_sections[section]:
                    for code in rendered_sections[section]:
                        parts.append(code.strip())
                        parts.append("")

        return "\n".join(parts)

    async def optimize_by_levels(
        self, composition_plan: CompositionPlan, file_structures: dict[str, FileStructure]
    ) -> OptimizedComposition:
        """Optimize template composition by levels.

        Args:
            composition_plan: Composition plan
            file_structures: File structures from composition

        Returns:
            Optimized composition result
        """
        optimized_files: dict[str, OptimizedFile] = {}
        optimization_log: list[str] = []

        # Group steps by file
        files_to_process = self._group_steps_by_file(composition_plan)

        for file_path, file_steps in files_to_process.items():
            # Sort steps by level priority
            sorted_steps = sorted(file_steps, key=lambda s: self._get_level_priority(s.level))

            # Optimize imports
            optimized_imports = self._optimize_imports(sorted_steps)
            optimization_log.append(
                f"Optimized {len(sorted_steps)} templates for {file_path}, "
                f"merged to {len(optimized_imports)} import statements"
            )

            # Get file structure
            file_structure = file_structures.get(file_path)
            if not file_structure:
                continue

            # Render primary template if it exists
            primary_rendered = None
            if file_structure.primary_template:
                # Find the context for the primary template
                primary_step = next(
                    (s for s in sorted_steps if s.level == TemplateLevel.FILE), None
                )
                if primary_step:
                    primary_rendered = file_structure.primary_template.render(primary_step.context)

            # Render template instances
            rendered_sections = await self._render_template_instances(file_structure)

            # Compose final code
            final_code = self._compose_file_code(
                file_structure, optimized_imports, rendered_sections, primary_rendered
            )

            optimized_files[file_path] = OptimizedFile(
                path=file_path,
                code=final_code,
                imports=optimized_imports,
                optimization_log=[f"Composed {len(sorted_steps)} templates"],
            )

        return OptimizedComposition(files=optimized_files, optimization_log=optimization_log)
