"""
Core interfaces and abstract base classes for the platform.

This module defines the core interfaces using modern Python typing features:
- Protocol-based interfaces for better duck typing
- Generic types with proper variance
- Modern union syntax (X | Y instead of Union[X, Y])
- Comprehensive type annotations
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from .models import (
    ActionRequest,
    ActionResult,
    ServiceDefinition,
    Simulation,
    SimulationSpec,
)


@runtime_checkable
class Template(Protocol):
    """Protocol for code templates with modern typing."""

    @property
    def name(self) -> str:
        """Return the unique template name, e.g., 'io/api_call'."""
        ...

    @property
    def input_schema(self) -> dict[str, str]:
        """Return input parameter types, e.g., {'url': 'str'}."""
        ...

    @property
    def output_schema(self) -> dict[str, str] | None:
        """Return output variable types, e.g., {'api_response': 'dict'}."""
        ...

    def render(self, params: dict[str, Any], context_variable_name: str | None = None) -> str:
        """Render template with parameters, return generated code."""
        ...


@runtime_checkable
class TemplateRegistry(Protocol):
    """Protocol for managing code templates."""

    async def get_template(self, name: str) -> Template:
        """Get template by name."""
        ...

    async def list_templates(self) -> Sequence[str]:
        """List all available template names."""
        ...

    async def register_template(self, template: Template) -> None:
        """Register a new template."""
        ...


@runtime_checkable
class CodeGenerator(Protocol):
    """Protocol for generating service code from definitions."""

    async def generate_service(self, service_def: ServiceDefinition) -> dict[str, str]:
        """Generate complete service code. Returns dict of filename -> content."""
        ...


@runtime_checkable
class Orchestrator(Protocol):
    """Protocol for deploying and managing simulations."""

    async def deploy_simulation(self, simulation: Simulation) -> None:
        """Deploy a simulation to the target environment."""
        ...

    async def destroy_simulation(self, simulation_id: str) -> None:
        """Destroy a simulation and clean up resources."""
        ...

    async def get_simulation_status(self, simulation_id: str) -> dict[str, Any]:
        """Get current status and topology of a simulation."""
        ...


@runtime_checkable
class TrafficGenerator(Protocol):
    """Protocol for generating traffic patterns."""

    async def start_traffic(self, simulation_id: str, pattern: dict[str, Any]) -> str:
        """Start traffic generation, return traffic job ID."""
        ...

    async def stop_traffic(self, traffic_job_id: str) -> None:
        """Stop traffic generation."""
        ...


@runtime_checkable
class ChaosEngine(Protocol):
    """Protocol for chaos engineering experiments."""

    async def inject_fault(self, simulation_id: str, experiment: dict[str, Any]) -> str:
        """Inject a fault, return experiment ID."""
        ...

    async def stop_experiment(self, experiment_id: str) -> None:
        """Stop a chaos experiment."""
        ...


@runtime_checkable
class LLMArchitect(Protocol):
    """Protocol for AI-assisted configuration generation."""

    async def generate_config(self, prompt: str) -> SimulationSpec:
        """Generate simulation configuration from natural language prompt."""
        ...

    async def validate_and_fix_config(
        self, config: SimulationSpec, errors: Sequence[str]
    ) -> SimulationSpec:
        """Validate and fix configuration based on validation errors."""
        ...


@runtime_checkable
class SimulationRepository(Protocol):
    """Protocol for simulation persistence."""

    async def save_simulation(self, simulation: Simulation) -> None:
        """Save simulation to storage."""
        ...

    async def get_simulation(self, simulation_id: str) -> Simulation | None:
        """Get simulation by ID."""
        ...

    async def list_simulations(self) -> Sequence[Simulation]:
        """List all simulations."""
        ...

    async def delete_simulation(self, simulation_id: str) -> None:
        """Delete simulation from storage."""
        ...


@runtime_checkable
class ActionExecutor(Protocol):
    """Protocol for executing actions within simulations."""

    async def execute_action(self, simulation_id: str, action: ActionRequest) -> ActionResult:
        """Execute an action in the specified simulation."""
        ...


@runtime_checkable
class VerificationEngine(Protocol):
    """Protocol for post-deployment verification."""

    async def verify_simulation(self, simulation_id: str) -> dict[str, Any]:
        """Verify simulation health and connectivity."""
        ...
