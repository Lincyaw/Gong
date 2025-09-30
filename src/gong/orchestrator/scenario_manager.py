"""
Scenario management for orchestrating timeline events.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..core.interfaces import ChaosEngine, TrafficGenerator
from ..core.models import Scenario, ScenarioEvent


class ScenarioManager:
    """Manages scenario execution with timeline events."""

    def __init__(self, traffic_generator: TrafficGenerator, chaos_engine: ChaosEngine):
        self.traffic_generator = traffic_generator
        self.chaos_engine = chaos_engine
        self.active_scenarios: dict[str, dict[str, Any]] = {}
        self.running_tasks: dict[str, list[asyncio.Task]] = {}

    async def start_scenario(self, simulation_id: str, scenario: Scenario) -> str:
        """Start executing a scenario."""
        scenario_id = str(uuid4())

        print(f"🎬 Starting scenario '{scenario.name}' for simulation {simulation_id}")

        # Store scenario info
        self.active_scenarios[scenario_id] = {
            "simulation_id": simulation_id,
            "scenario": scenario,
            "status": "running",
            "started_at": datetime.now(UTC),
            "events_executed": [],
        }

        # Start scenario execution task
        task = asyncio.create_task(self._execute_scenario(scenario_id, simulation_id, scenario))
        self.running_tasks[scenario_id] = [task]

        return scenario_id

    async def stop_scenario(self, scenario_id: str) -> None:
        """Stop a running scenario."""
        if scenario_id not in self.active_scenarios:
            return

        print(f"🛑 Stopping scenario {scenario_id}")

        # Cancel all running tasks
        if scenario_id in self.running_tasks:
            for task in self.running_tasks[scenario_id]:
                task.cancel()

            # Wait for tasks to complete
            try:
                await asyncio.gather(*self.running_tasks[scenario_id], return_exceptions=True)
            except Exception:
                pass

            del self.running_tasks[scenario_id]

        # Update status
        self.active_scenarios[scenario_id]["status"] = "stopped"

    async def get_scenario_status(self, scenario_id: str) -> dict[str, Any] | None:
        """Get scenario execution status."""
        if scenario_id not in self.active_scenarios:
            return None

        scenario_info = self.active_scenarios[scenario_id]

        return {
            "scenario_id": scenario_id,
            "simulation_id": scenario_info["simulation_id"],
            "name": scenario_info["scenario"].name,
            "status": scenario_info["status"],
            "started_at": scenario_info["started_at"].isoformat(),
            "events_executed": len(scenario_info["events_executed"]),
            "total_events": len(scenario_info["scenario"].events),
        }

    async def _execute_scenario(
        self, scenario_id: str, simulation_id: str, scenario: Scenario
    ) -> None:
        """Execute scenario timeline events."""
        try:
            scenario_info = self.active_scenarios[scenario_id]
            start_time = datetime.now(UTC)

            # Sort events by timestamp
            sorted_events = sorted(
                scenario.events, key=lambda e: self._parse_timestamp(e.timestamp)
            )

            for event in sorted_events:
                if scenario_info["status"] != "running":
                    break

                # Calculate when to execute this event
                event_time = self._parse_timestamp(event.timestamp)
                elapsed = (datetime.now(UTC) - start_time).total_seconds()

                if event_time > elapsed:
                    # Wait until it's time for this event
                    wait_time = event_time - elapsed
                    print(
                        f"⏰ Waiting {wait_time:.1f}s for event '{event.type}' in scenario {scenario_id}"
                    )
                    await asyncio.sleep(wait_time)

                if scenario_info["status"] != "running":
                    break

                # Execute the event
                await self._execute_event(scenario_id, simulation_id, event)
                scenario_info["events_executed"].append(
                    {
                        "event": event.model_dump(),
                        "executed_at": datetime.now(UTC).isoformat(),
                    }
                )

            # Mark scenario as completed
            scenario_info["status"] = "completed"
            print(f"✅ Scenario '{scenario.name}' completed")

        except asyncio.CancelledError:
            print(f"🛑 Scenario {scenario_id} was cancelled")
            raise
        except Exception as e:
            print(f"❌ Error executing scenario {scenario_id}: {e}")
            self.active_scenarios[scenario_id]["status"] = "failed"
            self.active_scenarios[scenario_id]["error"] = str(e)

    async def _execute_event(
        self, scenario_id: str, simulation_id: str, event: ScenarioEvent
    ) -> None:
        """Execute a single scenario event."""
        print(f"🎯 Executing {event.type} event in scenario {scenario_id}")

        try:
            if event.type == "traffic":
                await self._execute_traffic_event(simulation_id, event)
            elif event.type == "chaos":
                await self._execute_chaos_event(simulation_id, event)
            else:
                # Warning logged
                pass

        except Exception as e:
            print(f"❌ Error executing {event.type} event: {e}")
            raise

    async def _execute_traffic_event(self, simulation_id: str, event: ScenarioEvent) -> None:
        """Execute a traffic generation event."""
        config = event.config

        if hasattr(config, "model_dump"):
            pattern = config.model_dump()
        else:
            pattern = config

        job_id = await self.traffic_generator.start_traffic(simulation_id, pattern)
        print(f"🚦 Started traffic job {job_id}")

        # If the pattern has a duration, schedule stop
        duration = pattern.get("params", {}).get("duration")
        if duration:
            duration_seconds = self._parse_duration(duration)
            asyncio.create_task(self._stop_traffic_after_delay(job_id, duration_seconds))

    async def _execute_chaos_event(self, simulation_id: str, event: ScenarioEvent) -> None:
        """Execute a chaos engineering event."""
        config = event.config

        if hasattr(config, "model_dump"):
            experiment = config.model_dump()
        else:
            experiment = config

        experiment_id = await self.chaos_engine.inject_fault(simulation_id, experiment)
        print(f"🔥 Started chaos experiment {experiment_id}")

        # If the experiment has a duration, schedule stop
        duration = experiment.get("params", {}).get("duration")
        if duration:
            duration_seconds = self._parse_duration(duration)
            asyncio.create_task(self._stop_experiment_after_delay(experiment_id, duration_seconds))

    async def _stop_traffic_after_delay(self, job_id: str, delay_seconds: float) -> None:
        """Stop traffic generation after a delay."""
        await asyncio.sleep(delay_seconds)
        await self.traffic_generator.stop_traffic(job_id)
        print(f"🛑 Auto-stopped traffic job {job_id} after {delay_seconds}s")

    async def _stop_experiment_after_delay(self, experiment_id: str, delay_seconds: float) -> None:
        """Stop chaos experiment after a delay."""
        await asyncio.sleep(delay_seconds)
        await self.chaos_engine.stop_experiment(experiment_id)
        print(f"🛑 Auto-stopped chaos experiment {experiment_id} after {delay_seconds}s")

    def _parse_timestamp(self, timestamp: str) -> float:
        """Parse timestamp string to seconds from start."""
        # Handle relative timestamps like "5m", "30s", "1h"
        if timestamp.endswith("s"):
            return float(timestamp[:-1])
        elif timestamp.endswith("m"):
            return float(timestamp[:-1]) * 60
        elif timestamp.endswith("h"):
            return float(timestamp[:-1]) * 3600
        else:
            # Try to parse as number (assume seconds)
            try:
                return float(timestamp)
            except ValueError:
                # Warning logged
                return 0.0

    def _parse_duration(self, duration: str) -> float:
        """Parse duration string to seconds."""
        return self._parse_timestamp(duration)  # Same logic
