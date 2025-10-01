"""
In-memory repository implementations for development and testing.
"""

from ..core.interfaces import SimulationRepository
from ..core.models import Simulation


class InMemorySimulationRepository(SimulationRepository):
    """In-memory simulation repository for development."""

    def __init__(self) -> None:
        self._simulations: dict[str, Simulation] = {}

    async def save_simulation(self, simulation: Simulation) -> None:
        """Save simulation to memory."""
        self._simulations[str(simulation.id)] = simulation

    async def get_simulation(self, simulation_id: str) -> Simulation | None:
        """Get simulation by ID."""
        return self._simulations.get(simulation_id)

    async def list_simulations(self) -> list[Simulation]:
        """List all simulations."""
        return list(self._simulations.values())

    async def delete_simulation(self, simulation_id: str) -> None:
        """Delete simulation from memory."""
        self._simulations.pop(simulation_id, None)
