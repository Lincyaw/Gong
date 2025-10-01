"""
Dummy orchestrator for development and testing.
"""

import asyncio
from typing import Any

from ..core.interfaces import Orchestrator
from ..core.models import Simulation


class DummyOrchestrator(Orchestrator):
    """Dummy orchestrator for development."""

    def __init__(self) -> None:
        self.running_simulations: dict[str, dict[str, Any]] = {}
        self.simulations: dict[str, dict[str, Any]] = {}

    async def deploy_simulation(self, simulation: Simulation) -> None:
        """Deploy a simulation (dummy implementation)."""
        simulation_id = str(simulation.id)

        print(f"🚀 Deploying simulation {simulation.name} ({simulation_id})")

        # Simulate deployment steps
        print("  📦 Building container images...")
        await asyncio.sleep(1)

        print("  🏗️  Creating Kubernetes resources...")
        await asyncio.sleep(1)

        print("  🔧 Configuring services...")
        await asyncio.sleep(1)

        # Store simulation info
        self.simulations[simulation_id] = {
            "simulation": simulation,
            "status": "running",
            "services": [service.name for service in simulation.spec.services],
            "pods": self._generate_dummy_pods(simulation),
            "deployed_at": asyncio.get_event_loop().time(),
        }

        print(f"  ✅ Simulation {simulation.name} deployed successfully")

    async def destroy_simulation(self, simulation_id: str) -> None:
        """Destroy a simulation (dummy implementation)."""
        if simulation_id not in self.simulations:
            # Warning logged
            return

        print(f"🗑️  Destroying simulation {simulation_id}")

        # Simulate cleanup
        await asyncio.sleep(0.5)

        # Remove from tracking
        del self.simulations[simulation_id]

        print(f"  ✅ Simulation {simulation_id} destroyed")

    async def get_simulation_status(self, simulation_id: str) -> dict[str, Any]:
        """Get current status and topology of a simulation."""
        if simulation_id not in self.simulations:
            return {"error": "Simulation not found"}

        sim_info = self.simulations[simulation_id]
        simulation = sim_info["simulation"]

        # Generate dummy status
        return {
            "namespace": simulation.namespace,
            "status": sim_info["status"],
            "services": [
                {
                    "name": service_name,
                    "type": "ClusterIP",
                    "ports": [{"port": 80, "target_port": 8000}],
                }
                for service_name in sim_info["services"]
            ],
            "deployments": [
                {
                    "name": service.name,
                    "replicas": service.replicas,
                    "ready_replicas": service.replicas,
                    "available_replicas": service.replicas,
                }
                for service in simulation.spec.services
            ],
            "pods": sim_info["pods"],
            "uptime": asyncio.get_event_loop().time() - sim_info["deployed_at"],
        }

    def _generate_dummy_pods(self, simulation: Simulation) -> list:
        """Generate dummy pod information."""
        pods = []

        for service in simulation.spec.services:
            for i in range(service.replicas):
                pods.append(
                    {
                        "name": f"{service.name}-{i + 1}",
                        "status": "Running",
                        "ready": True,
                        "restarts": 0,
                        "age": "1m",
                    }
                )

        return pods
