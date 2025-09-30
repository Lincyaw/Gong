"""
Tests for chaos engineering engine.
"""

import pytest

from gong.chaos.engine import DummyChaosEngine


@pytest.fixture
def chaos_engine():
    """Create a chaos engine for testing."""
    return DummyChaosEngine()


@pytest.mark.asyncio
async def test_inject_pod_delete_fault(chaos_engine):
    """Test pod deletion fault injection."""
    experiment = {
        "type": "pod-delete",
        "target": {"service": "test-service"},
        "params": {"count": 1},
    }

    experiment_id = await chaos_engine.inject_fault("sim-test", experiment)

    assert experiment_id is not None
    assert experiment_id in chaos_engine.active_experiments
    assert chaos_engine.active_experiments[experiment_id]["status"] == "running"


@pytest.mark.asyncio
async def test_inject_network_latency_fault(chaos_engine):
    """Test network latency fault injection."""
    experiment = {
        "type": "network-latency",
        "target": {"service": "test-service"},
        "params": {"latency": "100ms", "duration": "5m"},
    }

    experiment_id = await chaos_engine.inject_fault("sim-test", experiment)

    assert experiment_id is not None
    assert chaos_engine.active_experiments[experiment_id]["type"] == "network-latency"


@pytest.mark.asyncio
async def test_stop_experiment(chaos_engine):
    """Test stopping a chaos experiment."""
    experiment = {
        "type": "pod-delete",
        "target": {"service": "test-service"},
        "params": {"count": 1},
    }

    experiment_id = await chaos_engine.inject_fault("sim-test", experiment)
    await chaos_engine.stop_experiment(experiment_id)

    assert chaos_engine.active_experiments[experiment_id]["status"] == "stopped"


@pytest.mark.asyncio
async def test_unknown_experiment_type(chaos_engine):
    """Test handling of unknown experiment types."""
    experiment = {"type": "unknown-type", "target": {"service": "test-service"}, "params": {}}

    # Should not raise an exception, just log and continue
    experiment_id = await chaos_engine.inject_fault("sim-test", experiment)
    assert experiment_id is not None
