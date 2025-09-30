"""
Tests for core models.
"""

from gong.core.models import (
    ServiceDefinition,
    ServiceEndpoint,
    Simulation,
    SimulationSpec,
    SimulationStatus,
    WorkflowStep,
)


def test_service_definition_creation():
    """Test ServiceDefinition model creation."""
    service = ServiceDefinition(
        name="test-service",
        replicas=2,
        endpoints=[
            ServiceEndpoint(
                path="/health",
                method="GET",
                workflow=[
                    WorkflowStep(
                        name="return_health",
                        template="control_flow/return_response",
                        params={"status_code": 200, "body": {"status": "ok"}},
                    )
                ],
            )
        ],
    )

    assert service.name == "test-service"
    assert service.replicas == 2
    assert len(service.endpoints) == 1
    assert service.endpoints[0].path == "/health"


def test_simulation_spec_creation():
    """Test SimulationSpec model creation."""
    spec = SimulationSpec(
        name="test-simulation",
        description="Test simulation",
        services=[ServiceDefinition(name="service1"), ServiceDefinition(name="service2")],
    )

    assert spec.name == "test-simulation"
    assert len(spec.services) == 2


def test_simulation_creation():
    """Test Simulation model creation."""
    spec = SimulationSpec(name="test-sim")
    simulation = Simulation(name="test-simulation", spec=spec)

    assert simulation.name == "test-simulation"
    assert simulation.status == SimulationStatus.PENDING
    assert simulation.namespace.startswith("sim-")
    assert len(simulation.namespace) == 12  # "sim-" + 8 chars from UUID


def test_simulation_namespace_generation():
    """Test automatic namespace generation."""
    spec = SimulationSpec(name="test")
    sim1 = Simulation(name="sim1", spec=spec)
    sim2 = Simulation(name="sim2", spec=spec)

    # Namespaces should be different
    assert sim1.namespace != sim2.namespace
    assert sim1.namespace.startswith("sim-")
    assert sim2.namespace.startswith("sim-")
