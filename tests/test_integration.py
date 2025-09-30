"""
Integration tests for the simulation platform.
"""

import asyncio
from uuid import uuid4

import pytest

from gong.api.dependencies import get_dependencies
from gong.core.models import (
    Scenario,
    ScenarioEvent,
    ServiceDefinition,
    ServiceEndpoint,
    SimulationSpec,
    TrafficPattern,
    WorkflowStep,
)


@pytest.fixture
def sample_simulation_spec():
    """Create a sample simulation spec for testing."""
    return SimulationSpec(
        name="integration-test-simulation",
        description="Integration test simulation",
        services=[
            ServiceDefinition(
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
                                params={"status_code": 200, "body": {"status": "healthy"}},
                            )
                        ],
                    )
                ],
            )
        ],
        scenario=Scenario(
            name="test-scenario",
            events=[
                ScenarioEvent(
                    timestamp="0s",
                    type="traffic",
                    config=TrafficPattern(
                        name="baseline", type="constant", params={"users": 5, "duration": "10s"}
                    ),
                )
            ],
        ),
    )


@pytest.mark.asyncio
async def test_full_simulation_lifecycle(sample_simulation_spec):
    """Test the complete simulation lifecycle."""
    deps = get_dependencies()

    # 1. Create simulation
    from gong.core.models import Simulation

    simulation = Simulation(name="integration-test", spec=sample_simulation_spec)

    # 2. Save simulation
    await deps.simulation_repo.save_simulation(simulation)

    # 3. Generate code for services
    for service_def in simulation.spec.services:
        generated_code = await deps.code_generator.generate_service(service_def)
        assert "src/main.py" in generated_code
        assert "requirements.txt" in generated_code
        assert "Dockerfile" in generated_code

    # 4. Deploy simulation (dummy)
    await deps.orchestrator.deploy_simulation(simulation)

    # 5. Verify simulation
    verification_result = await deps.verification_engine.verify_simulation(str(simulation.id))
    assert verification_result["overall_status"] == "pass"

    # 6. Start scenario
    if simulation.spec.scenario:
        scenario_id = await deps.scenario_manager.start_scenario(
            str(simulation.id), simulation.spec.scenario
        )
        assert scenario_id is not None

        # Check scenario status
        scenario_status = await deps.scenario_manager.get_scenario_status(scenario_id)
        assert scenario_status["status"] == "running"

        # Stop scenario
        await deps.scenario_manager.stop_scenario(scenario_id)

    # 7. Test action execution
    from gong.core.models import ActionRequest

    action = ActionRequest(action_type="kubectl_get", params={"resource_type": "pods"})

    action_result = await deps.action_executor.execute_action(str(simulation.id), action)
    assert action_result.status == "COMPLETED"

    # 8. Clean up
    await deps.orchestrator.destroy_simulation(str(simulation.id))
    await deps.simulation_repo.delete_simulation(str(simulation.id))


@pytest.mark.asyncio
async def test_llm_architect_integration():
    """Test LLM architect integration."""
    deps = get_dependencies()

    # Generate config from prompt
    prompt = "Create a simple web service with health check"
    spec = await deps.llm_architect.generate_config(prompt)

    assert spec.name is not None
    assert len(spec.services) > 0

    # Validate generated spec
    service = spec.services[0]
    assert service.name is not None
    assert service.replicas >= 1
    assert len(service.endpoints) > 0


@pytest.mark.asyncio
async def test_template_system_integration():
    """Test template system integration."""
    deps = get_dependencies()

    # List templates
    templates = await deps.template_registry.list_templates()
    assert len(templates) > 0
    assert "io/http_api_call" in templates
    assert "control_flow/return_response" in templates

    # Get and render a template
    template = await deps.template_registry.get_template("io/http_api_call")
    code = template.render(
        {"target_service": "user-service", "path": "/v1/users/123", "method": "GET"}
    )

    assert "user-service" in code
    assert "/v1/users/123" in code


@pytest.mark.asyncio
async def test_chaos_and_traffic_integration():
    """Test chaos engineering and traffic generation integration."""
    deps = get_dependencies()

    simulation_id = str(uuid4())

    # Start traffic
    traffic_pattern = {"type": "constant", "params": {"users": 10, "duration": "5s"}}

    traffic_job_id = await deps.traffic_generator.start_traffic(simulation_id, traffic_pattern)
    assert traffic_job_id is not None

    # Inject chaos
    chaos_experiment = {
        "type": "pod-delete",
        "target": {"service": "test-service"},
        "params": {"count": 1},
    }

    experiment_id = await deps.chaos_engine.inject_fault(simulation_id, chaos_experiment)
    assert experiment_id is not None

    # Wait briefly
    await asyncio.sleep(0.1)

    # Clean up
    await deps.traffic_generator.stop_traffic(traffic_job_id)
    await deps.chaos_engine.stop_experiment(experiment_id)


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in various components."""
    deps = get_dependencies()

    # Test with non-existent simulation
    await deps.verification_engine.verify_simulation("nonexistent")
    # Should not raise exception, should return error status

    # Test action on non-existent simulation
    from gong.core.models import ActionRequest

    action = ActionRequest(action_type="kubectl_get")

    # This should work with dummy executor
    result = await deps.action_executor.execute_action("nonexistent", action)
    assert result.status in ["COMPLETED", "FAILED"]

    # Test stopping non-existent traffic
    await deps.traffic_generator.stop_traffic("nonexistent")

    # Test stopping non-existent chaos experiment
    await deps.chaos_engine.stop_experiment("nonexistent")


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent operations."""
    deps = get_dependencies()

    simulation_id = str(uuid4())

    # Start multiple traffic jobs concurrently
    traffic_tasks = []
    for i in range(3):
        pattern = {"type": "constant", "params": {"users": 5, "duration": "2s"}}
        task = deps.traffic_generator.start_traffic(f"{simulation_id}-{i}", pattern)
        traffic_tasks.append(task)

    # Wait for all to start
    job_ids = await asyncio.gather(*traffic_tasks)
    assert len(job_ids) == 3

    # Stop all concurrently
    stop_tasks = [deps.traffic_generator.stop_traffic(job_id) for job_id in job_ids]
    await asyncio.gather(*stop_tasks)
