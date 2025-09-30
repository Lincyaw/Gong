"""
Main FastAPI application for the simulation platform.
"""

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from ..core.models import ActionRequest, ActionResult, Simulation, SimulationSpec, SimulationStatus
from .dependencies import Dependencies, get_dependencies

app = FastAPI(
    title="Microservice Simulation Platform",
    description="AI-powered platform for generating dynamic microservice environments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    summary="Generate and manage microservice simulations for AIOps research and LLM training",
    contact={
        "name": "Platform Team",
        "email": "team@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the simulation platform is healthy and operational",
    response_description="Health status information",
)
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "simulation-platform",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post(
    "/api/v1/simulations",
    response_model=dict[str, str],
    tags=["Simulations"],
    status_code=status.HTTP_201_CREATED,
    summary="Create Simulation",
    description="Create and deploy a new microservice simulation environment",
    response_description="Simulation creation confirmation with ID and status",
)
async def create_simulation(
    spec: SimulationSpec,
    background_tasks: BackgroundTasks,
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> dict[str, str]:
    """Create and deploy a new simulation environment."""

    # Create simulation instance
    simulation = Simulation(name=spec.name, spec=spec, status=SimulationStatus.PENDING)

    # Save to repository
    await deps.simulation_repo.save_simulation(simulation)

    # Start deployment in background
    background_tasks.add_task(deploy_simulation_task, simulation.id, deps)

    return {"simulation_id": str(simulation.id), "status": simulation.status.value}


@app.get("/api/v1/simulations/{simulation_id}", tags=["Simulations"])
async def get_simulation(
    simulation_id: str, deps: Annotated[Dependencies, Depends(get_dependencies)]
) -> dict[str, Any]:
    """Get simulation details and status."""

    simulation = await deps.simulation_repo.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Get runtime status from orchestrator
    runtime_status = await deps.orchestrator.get_simulation_status(simulation_id)

    return {
        "id": str(simulation.id),
        "name": simulation.name,
        "status": simulation.status.value,
        "namespace": simulation.namespace,
        "created_at": simulation.created_at.isoformat(),
        "updated_at": simulation.updated_at.isoformat(),
        "error_message": simulation.error_message,
        "topology": runtime_status,
    }


@app.get("/api/v1/simulations", tags=["Simulations"])
async def list_simulations(
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> list[dict[str, Any]]:
    """List all simulations."""

    simulations = await deps.simulation_repo.list_simulations()

    return [
        {
            "id": str(sim.id),
            "name": sim.name,
            "status": sim.status.value,
            "created_at": sim.created_at.isoformat(),
        }
        for sim in simulations
    ]


@app.delete("/api/v1/simulations/{simulation_id}", tags=["Simulations"])
async def delete_simulation(
    simulation_id: str,
    background_tasks: BackgroundTasks,
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> dict[str, str]:
    """Delete a simulation environment."""

    simulation = await deps.simulation_repo.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Start destruction in background
    background_tasks.add_task(destroy_simulation_task, simulation_id, deps)

    return {"message": "Deletion scheduled"}


@app.post("/api/v1/simulations/{simulation_id}/actions", tags=["Actions"])
async def execute_action(
    simulation_id: str,
    action: ActionRequest,
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> ActionResult:
    """Execute an action within a simulation (for LLM agents)."""

    simulation = await deps.simulation_repo.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Simulation is not running")

    # Execute action using action executor
    result = await deps.action_executor.execute_action(simulation_id, action)

    return result


@app.get("/api/v1/templates", tags=["Templates"])
async def list_templates(deps: Annotated[Dependencies, Depends(get_dependencies)]) -> list[str]:
    """List available code templates."""
    return await deps.template_registry.list_templates()


@app.post("/api/v1/simulations/{simulation_id}/verify", tags=["Verification"])
async def verify_simulation(
    simulation_id: str, deps: Annotated[Dependencies, Depends(get_dependencies)]
) -> dict[str, Any]:
    """Verify simulation health and connectivity."""

    simulation = await deps.simulation_repo.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    # Run verification
    verification_result = await deps.verification_engine.verify_simulation(simulation_id)

    return verification_result


@app.post("/api/v1/simulations/{simulation_id}/traffic", tags=["Traffic"])
async def start_traffic(
    simulation_id: str,
    pattern: dict[str, Any],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> dict[str, str]:
    """Start traffic generation for a simulation."""

    simulation = await deps.simulation_repo.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Simulation is not running")

    # Start traffic generation
    job_id = await deps.traffic_generator.start_traffic(simulation_id, pattern)

    return {"traffic_job_id": job_id, "status": "started"}


@app.delete("/api/v1/traffic/{job_id}", tags=["Traffic"])
async def stop_traffic(
    job_id: str, deps: Annotated[Dependencies, Depends(get_dependencies)]
) -> dict[str, str]:
    """Stop traffic generation."""

    await deps.traffic_generator.stop_traffic(job_id)

    return {"message": "Traffic generation stopped"}


@app.post("/api/v1/simulations/{simulation_id}/chaos", tags=["Chaos"])
async def inject_chaos(
    simulation_id: str,
    experiment: dict[str, Any],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> dict[str, str]:
    """Inject chaos experiment into a simulation."""

    simulation = await deps.simulation_repo.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Simulation is not running")

    # Inject chaos
    experiment_id = await deps.chaos_engine.inject_fault(simulation_id, experiment)

    return {"experiment_id": experiment_id, "status": "started"}


@app.delete("/api/v1/chaos/{experiment_id}", tags=["Chaos"])
async def stop_chaos(
    experiment_id: str, deps: Annotated[Dependencies, Depends(get_dependencies)]
) -> dict[str, str]:
    """Stop chaos experiment."""

    await deps.chaos_engine.stop_experiment(experiment_id)

    return {"message": "Chaos experiment stopped"}


@app.post("/api/v1/simulations/{simulation_id}/scenario", tags=["Scenarios"])
async def start_scenario(
    simulation_id: str,
    scenario: dict[str, Any],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
) -> dict[str, str]:
    """Start a scenario for a simulation."""

    simulation = await deps.simulation_repo.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if simulation.status != SimulationStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Simulation is not running")

    # Parse scenario
    from ..core.models import Scenario

    scenario_obj = Scenario(**scenario)

    # Start scenario
    scenario_id = await deps.scenario_manager.start_scenario(simulation_id, scenario_obj)

    return {"scenario_id": scenario_id, "status": "started"}


@app.get("/api/v1/scenarios/{scenario_id}", tags=["Scenarios"])
async def get_scenario_status(
    scenario_id: str, deps: Annotated[Dependencies, Depends(get_dependencies)]
) -> dict[str, Any]:
    """Get scenario execution status."""

    status = await deps.scenario_manager.get_scenario_status(scenario_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return status


@app.delete("/api/v1/scenarios/{scenario_id}", tags=["Scenarios"])
async def stop_scenario(
    scenario_id: str, deps: Annotated[Dependencies, Depends(get_dependencies)]
) -> dict[str, str]:
    """Stop a running scenario."""

    await deps.scenario_manager.stop_scenario(scenario_id)

    return {"message": "Scenario stopped"}


@app.post("/api/v1/generate", tags=["AI"])
async def generate_config(
    prompt: dict[str, str], deps: Annotated[Dependencies, Depends(get_dependencies)]
) -> dict[str, Any]:
    """Generate simulation configuration from natural language prompt."""

    user_prompt = prompt.get("prompt", "")
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Generate configuration using LLM architect
    spec = await deps.llm_architect.generate_config(user_prompt)

    return {"generated_spec": spec.model_dump(), "message": "Configuration generated successfully"}


async def deploy_simulation_task(simulation_id: UUID, deps) -> None:
    """Background task to deploy a simulation."""
    try:
        simulation = await deps.simulation_repo.get_simulation(str(simulation_id))
        if not simulation:
            return

        # Update status to building
        simulation.status = SimulationStatus.BUILDING
        await deps.simulation_repo.save_simulation(simulation)

        # Generate code for each service
        for service_def in simulation.spec.services:
            await deps.code_generator.generate_service(service_def)
            # In a real implementation, this would build and push Docker images

        # Update status to deploying
        simulation.status = SimulationStatus.DEPLOYING
        await deps.simulation_repo.save_simulation(simulation)

        # Deploy to orchestrator
        await deps.orchestrator.deploy_simulation(simulation)

        # Run post-deployment verification
        verification_result = await deps.verification_engine.verify_simulation(str(simulation_id))

        if verification_result.get("overall_status") == "pass":
            # Update final status
            simulation.status = SimulationStatus.RUNNING
            await deps.simulation_repo.save_simulation(simulation)

            # Start scenario if defined
            if simulation.spec.scenario:
                scenario_id = await deps.scenario_manager.start_scenario(
                    str(simulation_id), simulation.spec.scenario
                )
                print(f"🎬 Started scenario {scenario_id} for simulation {simulation_id}")
        else:
            # Verification failed
            simulation.status = SimulationStatus.FAILED
            simulation.error_message = (
                f"Verification failed: {verification_result.get('error', 'Unknown error')}"
            )
            await deps.simulation_repo.save_simulation(simulation)

    except Exception as e:
        # Update error status
        simulation.status = SimulationStatus.FAILED
        simulation.error_message = str(e)
        await deps.simulation_repo.save_simulation(simulation)


async def destroy_simulation_task(simulation_id: str, deps) -> None:
    """Background task to destroy a simulation."""
    try:
        simulation = await deps.simulation_repo.get_simulation(simulation_id)
        if not simulation:
            return

        # Update status
        simulation.status = SimulationStatus.STOPPING
        await deps.simulation_repo.save_simulation(simulation)

        # Destroy in orchestrator
        await deps.orchestrator.destroy_simulation(simulation_id)

        # Delete from repository
        await deps.simulation_repo.delete_simulation(simulation_id)

    except Exception:
        # Log error but don't fail
        pass


def main():
    """Main entry point for the API server."""
    import uvicorn

    from ..config import get_config

    config = get_config()
    uvicorn.run(app, host=config.api_host, port=config.api_port)


if __name__ == "__main__":
    main()
