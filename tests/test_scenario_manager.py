"""
Tests for scenario manager.
"""

import asyncio

import pytest

from gong.chaos.engine import DummyChaosEngine
from gong.core.models import ChaosExperiment, Scenario, ScenarioEvent, TrafficPattern
from gong.orchestrator.scenario_manager import ScenarioManager
from gong.traffic.generator import DummyTrafficGenerator


@pytest.fixture
def scenario_manager():
    """Create a scenario manager for testing."""
    traffic_generator = DummyTrafficGenerator()
    chaos_engine = DummyChaosEngine()
    return ScenarioManager(traffic_generator, chaos_engine)


@pytest.fixture
def sample_scenario():
    """Create a sample scenario for testing."""
    return Scenario(
        name="test-scenario",
        description="Test scenario",
        events=[
            ScenarioEvent(
                timestamp="0s",
                type="traffic",
                config=TrafficPattern(
                    name="baseline", type="constant", params={"users": 10, "duration": "5s"}
                ),
            ),
            ScenarioEvent(
                timestamp="2s",
                type="chaos",
                config=ChaosExperiment(
                    name="pod-failure",
                    type="pod-delete",
                    target={"service": "test-service"},
                    params={"count": 1},
                ),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_start_scenario(scenario_manager, sample_scenario):
    """Test starting a scenario."""
    scenario_id = await scenario_manager.start_scenario("sim-test", sample_scenario)

    assert scenario_id is not None
    assert scenario_id in scenario_manager.active_scenarios

    scenario_info = scenario_manager.active_scenarios[scenario_id]
    assert scenario_info["status"] == "running"
    assert scenario_info["simulation_id"] == "sim-test"


@pytest.mark.asyncio
async def test_get_scenario_status(scenario_manager, sample_scenario):
    """Test getting scenario status."""
    scenario_id = await scenario_manager.start_scenario("sim-test", sample_scenario)

    status = await scenario_manager.get_scenario_status(scenario_id)

    assert status is not None
    assert status["scenario_id"] == scenario_id
    assert status["simulation_id"] == "sim-test"
    assert status["name"] == "test-scenario"
    assert "events_executed" in status
    assert "total_events" in status


@pytest.mark.asyncio
async def test_stop_scenario(scenario_manager, sample_scenario):
    """Test stopping a scenario."""
    scenario_id = await scenario_manager.start_scenario("sim-test", sample_scenario)

    # Let it run briefly
    await asyncio.sleep(0.1)

    await scenario_manager.stop_scenario(scenario_id)

    scenario_info = scenario_manager.active_scenarios[scenario_id]
    assert scenario_info["status"] == "stopped"


@pytest.mark.asyncio
async def test_get_nonexistent_scenario_status(scenario_manager):
    """Test getting status of non-existent scenario."""
    status = await scenario_manager.get_scenario_status("nonexistent-id")
    assert status is None


@pytest.mark.asyncio
async def test_parse_timestamp(scenario_manager):
    """Test timestamp parsing."""
    assert scenario_manager._parse_timestamp("30s") == 30.0
    assert scenario_manager._parse_timestamp("5m") == 300.0
    assert scenario_manager._parse_timestamp("1h") == 3600.0
    assert scenario_manager._parse_timestamp("invalid") == 0.0


@pytest.mark.asyncio
async def test_scenario_execution_order(scenario_manager):
    """Test that scenario events execute in correct order."""
    # Create scenario with events at different times
    scenario = Scenario(
        name="order-test",
        events=[
            ScenarioEvent(
                timestamp="1s", type="traffic", config={"type": "constant", "params": {"users": 5}}
            ),
            ScenarioEvent(
                timestamp="0s",  # This should execute first
                type="traffic",
                config={"type": "constant", "params": {"users": 1}},
            ),
        ],
    )

    scenario_id = await scenario_manager.start_scenario("sim-test", scenario)

    # Let scenario run briefly
    await asyncio.sleep(0.1)

    # Check that scenario is running
    status = await scenario_manager.get_scenario_status(scenario_id)
    assert status["status"] == "running"

    await scenario_manager.stop_scenario(scenario_id)
