"""
Core domain models for the microservice simulation platform.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


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

    name: str
    description: str | None = None
    services: list[ServiceDefinition] = Field(default_factory=list)
    scenario: Scenario | None = None
    global_config: dict[str, Any] = Field(default_factory=dict)


class Simulation(BaseModel):
    """Runtime simulation instance."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    status: SimulationStatus = SimulationStatus.PENDING
    spec: SimulationSpec
    namespace: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error_message: str | None = None

    @validator("namespace", always=True)
    def generate_namespace(cls, v: str | None, values: dict[str, Any]) -> str:
        """Generate namespace from simulation ID if not provided."""
        if v is None and "id" in values:
            return f"sim-{str(values['id'])[:8]}"
        return v or "default"


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
    executed_at: datetime = Field(default_factory=datetime.utcnow)
