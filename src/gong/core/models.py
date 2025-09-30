"""
Core domain models for the microservice simulation platform.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field


class SimulationStatus(str, Enum):
    """Simulation lifecycle status."""

    PENDING = "PENDING"
    BUILDING = "BUILDING"
    DEPLOYING = "DEPLOYING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class ProvisioningMode(str, Enum):
    """Datastore provisioning mode."""

    DYNAMIC = "dynamic"
    EXTERNAL = "external"


class TeardownPolicy(str, Enum):
    """Resource teardown policy."""

    DELETE_PVC = "deletePvc"
    RETAIN_PVC = "retainPvc"


class FaultType(str, Enum):
    """Types of faults that can be injected."""

    LATENCY = "latency"
    ERROR = "error"
    CORRUPT_RESPONSE = "corrupt_response"


class ResourceRequirements(BaseModel):
    """Kubernetes resource requirements."""

    cpu: str = "100m"
    memory: str = "128Mi"


class ResourceSpec(BaseModel):
    """Resource specification for services."""

    requests: ResourceRequirements = Field(default_factory=ResourceRequirements)
    limits: ResourceRequirements = Field(default_factory=ResourceRequirements)


class DatastoreProvisioning(BaseModel):
    """Datastore provisioning configuration."""

    mode: ProvisioningMode = ProvisioningMode.DYNAMIC
    chart: str | None = None
    initialization: dict[str, Any] | None = None


class DatastoreDependency(BaseModel):
    """Datastore dependency definition."""

    name: str
    type: str  # postgres, redis, mongodb, etc.
    provisioning: DatastoreProvisioning = Field(default_factory=DatastoreProvisioning)
    teardown_policy: TeardownPolicy = TeardownPolicy.DELETE_PVC


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    logging: dict[str, Any] = Field(default_factory=lambda: {"level": "INFO", "format": "JSON"})
    tracing: dict[str, Any] = Field(default_factory=lambda: {"sampling_rate": 0.1})
    metrics: dict[str, Any] = Field(default_factory=dict)


class FaultInjection(BaseModel):
    """Fault injection configuration."""

    type: FaultType
    probability: float = Field(ge=0.0, le=1.0)
    value: str  # e.g., "normal(150, 20)" for latency


class WorkflowStep(BaseModel):
    """A single step in a service workflow."""

    name: str
    template: str
    params: dict[str, Any] = Field(default_factory=dict)
    output: str | None = None
    inject_faults: list[FaultInjection] = Field(default_factory=list)
    on_failure: str | None = None


class ServiceEndpoint(BaseModel):
    """Service endpoint definition."""

    path: str
    method: str = "GET"
    workflow: list[WorkflowStep] = Field(default_factory=list)


class ServiceDefinition(BaseModel):
    """Complete service definition."""

    name: str
    replicas: int = 1
    resources: ResourceSpec = Field(default_factory=ResourceSpec)
    dependencies: dict[str, list[str | DatastoreDependency]] = Field(
        default_factory=lambda: {"services": [], "datastores": []}  # type: ignore
    )
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    endpoints: list[ServiceEndpoint] = Field(default_factory=list)

    @property
    def namespace(self) -> str:
        """Get namespace for this service (will be set by simulation)."""
        return getattr(self, "_namespace", "default")


class TrafficPattern(BaseModel):
    """Traffic generation pattern."""

    name: str
    type: str  # constant, ramp, spike, etc.
    params: dict[str, Any] = Field(default_factory=dict)
    duration: str | None = None


class ChaosExperiment(BaseModel):
    """Chaos engineering experiment definition."""

    name: str
    type: str  # pod-delete, network-latency, etc.
    target: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)


class ScenarioEvent(BaseModel):
    """A timed event in a scenario."""

    timestamp: str  # relative time like "5m" or absolute
    type: str  # traffic, chaos, etc.
    config: TrafficPattern | ChaosExperiment


class Scenario(BaseModel):
    """Complete scenario definition with timeline."""

    name: str
    description: str | None = None
    events: list[ScenarioEvent] = Field(default_factory=list)


class SimulationSpec(BaseModel):
    """Complete simulation specification."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    name: str = Field(min_length=1, description="Simulation name cannot be empty")
    description: str | None = Field(None, description="Optional description of the simulation")
    services: list[ServiceDefinition] = Field(
        default_factory=list, description="List of microservices to deploy"
    )
    scenario: Scenario | None = Field(None, description="Optional scenario for dynamic behavior")
    global_config: dict[str, Any] = Field(
        default_factory=dict, description="Global configuration settings"
    )

    @computed_field
    @property
    def service_count(self) -> int:
        """Number of services in this simulation."""
        return len(self.services)


class Simulation(BaseModel):
    """Runtime simulation instance."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4, description="Unique simulation identifier")
    name: str = Field(description="Human-readable simulation name")
    status: SimulationStatus = Field(
        default=SimulationStatus.PENDING, description="Current simulation status"
    )
    spec: SimulationSpec = Field(description="Simulation specification")
    namespace: str | None = Field(None, description="Kubernetes namespace")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When the simulation was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the simulation was last updated",
    )
    error_message: str | None = Field(None, description="Error message if simulation failed")

    def __init__(self, **data: Any) -> None:
        """Initialize simulation with auto-generated namespace if not provided."""
        if "namespace" not in data or data["namespace"] is None:
            if "id" in data:
                data["namespace"] = f"sim-{str(data['id'])[:8]}"
            else:
                # Generate a temporary ID for namespace generation
                temp_id = uuid4()
                data["namespace"] = f"sim-{str(temp_id)[:8]}"
        super().__init__(**data)

    @computed_field
    @property
    def is_active(self) -> bool:
        """Whether the simulation is currently active."""
        return self.status in [
            SimulationStatus.BUILDING,
            SimulationStatus.DEPLOYING,
            SimulationStatus.RUNNING,
        ]


class ActionRequest(BaseModel):
    """Request to execute an action in a simulation."""

    action_type: str
    target: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    """Result of an executed action."""

    action_id: UUID = Field(default_factory=uuid4)
    status: str
    result: Any | None = None
    error: str | None = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
