"""
Unit tests for core models.
"""

from uuid import UUID

import pytest

from gong.core.models import (
    FaultInjection,
    FaultType,
    ServiceDefinition,
    ServiceEndpoint,
    Simulation,
    SimulationSpec,
    SimulationStatus,
    WorkflowStep,
)


class TestServiceDefinition:
    """Test ServiceDefinition model."""

    def test_create_basic_service(self):
        """Test creating a basic service definition."""
        service = ServiceDefinition(name="test-service")

        assert service.name == "test-service"
        assert service.replicas == 1
        assert service.endpoints == []
        assert service.dependencies == {"services": [], "datastores": []}

    def test_create_service_with_endpoints(self):
        """Test creating a service with endpoints."""
        endpoint = ServiceEndpoint(
            path="/api/test",
            method="GET",
            workflow=[
                WorkflowStep(
                    name="test_step",
                    template="io/http_api_call",
                    params={"url": "http://example.com"},
                )
            ],
        )

        service = ServiceDefinition(name="test-service", replicas=3, endpoints=[endpoint])

        assert service.name == "test-service"
        assert service.replicas == 3
        assert len(service.endpoints) == 1
        assert service.endpoints[0].path == "/api/test"
        assert service.endpoints[0].method == "GET"
        assert len(service.endpoints[0].workflow) == 1

    def test_workflow_step_with_fault_injection(self):
        """Test workflow step with fault injection."""
        fault = FaultInjection(type=FaultType.LATENCY, probability=0.1, value="normal(100, 20)")

        step = WorkflowStep(
            name="test_step",
            template="io/http_api_call",
            params={"url": "http://example.com"},
            inject_faults=[fault],
        )

        assert step.name == "test_step"
        assert step.template == "io/http_api_call"
        assert len(step.inject_faults) == 1
        assert step.inject_faults[0].type == FaultType.LATENCY
        assert step.inject_faults[0].probability == 0.1


class TestSimulation:
    """Test Simulation model."""

    def test_create_simulation(self):
        """Test creating a simulation."""
        spec = SimulationSpec(
            name="test-simulation",
            description="Test simulation",
            services=[ServiceDefinition(name="service1"), ServiceDefinition(name="service2")],
        )

        simulation = Simulation(name="test-sim", spec=spec)

        assert simulation.name == "test-sim"
        assert simulation.status == SimulationStatus.PENDING
        assert isinstance(simulation.id, UUID)
        assert simulation.spec.name == "test-simulation"
        assert len(simulation.spec.services) == 2

    def test_simulation_namespace_generation(self):
        """Test automatic namespace generation."""
        spec = SimulationSpec(name="test-simulation")
        simulation = Simulation(name="test-sim", spec=spec)

        # Namespace should be generated from simulation ID
        assert simulation.namespace.startswith("sim-")
        assert len(simulation.namespace) == 12  # "sim-" + 8 chars from UUID

    def test_simulation_status_transitions(self):
        """Test simulation status transitions."""
        spec = SimulationSpec(name="test-simulation")
        simulation = Simulation(name="test-sim", spec=spec)

        # Initial status
        assert simulation.status == SimulationStatus.PENDING

        # Update status
        simulation.status = SimulationStatus.RUNNING
        assert simulation.status == SimulationStatus.RUNNING


class TestFaultInjection:
    """Test FaultInjection model."""

    def test_latency_fault(self):
        """Test latency fault injection."""
        fault = FaultInjection(type=FaultType.LATENCY, probability=0.05, value="fixed(500)")

        assert fault.type == FaultType.LATENCY
        assert fault.probability == 0.05
        assert fault.value == "fixed(500)"

    def test_error_fault(self):
        """Test error fault injection."""
        fault = FaultInjection(type=FaultType.ERROR, probability=0.02, value="http_500")

        assert fault.type == FaultType.ERROR
        assert fault.probability == 0.02
        assert fault.value == "http_500"

    def test_probability_validation(self):
        """Test probability validation."""
        # Valid probabilities
        FaultInjection(type=FaultType.LATENCY, probability=0.0, value="test")
        FaultInjection(type=FaultType.LATENCY, probability=0.5, value="test")
        FaultInjection(type=FaultType.LATENCY, probability=1.0, value="test")

        # Invalid probabilities should raise validation error
        with pytest.raises(ValueError):
            FaultInjection(type=FaultType.LATENCY, probability=-0.1, value="test")

        with pytest.raises(ValueError):
            FaultInjection(type=FaultType.LATENCY, probability=1.1, value="test")
