"""
Integration tests for demo functionality.
"""

import pytest

from gong.api.dependencies import get_dependencies


class TestDemoIntegration:
    """Test demo integration scenarios."""

    @pytest.fixture
    def deps(self):
        """Get platform dependencies."""
        return get_dependencies()

    async def test_template_system_integration(self, deps):
        """Test template system integration."""
        # List available templates
        templates = await deps.template_registry.list_templates()
        assert len(templates) > 0
        assert "io/http_api_call" in templates

        # Get and render a template
        template = await deps.template_registry.get_template("io/http_api_call")
        code = template.render({"target_service": "test-service", "path": "/test", "method": "GET"})

        assert "test-service" in code
        assert "/test" in code

    async def test_code_generation_integration(self, deps):
        """Test code generation integration."""
        from gong.core.models import ServiceDefinition, ServiceEndpoint, WorkflowStep

        # Create a test service
        service_def = ServiceDefinition(
            name="integration-test-service",
            endpoints=[
                ServiceEndpoint(
                    path="/test",
                    method="GET",
                    workflow=[
                        WorkflowStep(
                            name="return_test",
                            template="control_flow/return_response",
                            params={"status_code": 200, "body": {"message": "test"}},
                        )
                    ],
                )
            ],
        )

        # Generate service code
        files = await deps.code_generator.generate_service(service_def)

        # Verify generated files
        assert "src/main.py" in files
        assert "requirements.txt" in files
        assert "Dockerfile" in files

        # Verify main.py content
        main_py = files["src/main.py"]
        assert "FastAPI" in main_py
        assert "integration-test-service" in main_py
        assert '@app.get("/test")' in main_py

    async def test_llm_architect_integration(self, deps):
        """Test LLM architect integration."""
        # Generate a simulation spec
        spec = await deps.llm_architect.generate_config(
            "Create a simple web service with health check"
        )

        assert spec.name is not None
        assert len(spec.services) > 0

        # Verify the generated service has basic structure
        service = spec.services[0]
        assert service.name is not None
        assert len(service.endpoints) > 0

    async def test_full_workflow_integration(self, deps):
        """Test full workflow from prompt to code generation."""
        # 1. Generate config from prompt
        spec = await deps.llm_architect.generate_config("Create a user management service")

        # 2. Generate code for each service
        all_files = {}
        for service_def in spec.services:
            files = await deps.code_generator.generate_service(service_def)
            all_files[service_def.name] = files

        # 3. Verify we have generated code
        assert len(all_files) > 0

        for service_name, files in all_files.items():
            assert "src/main.py" in files
            assert "requirements.txt" in files

            # Verify the main.py is valid Python-like code
            main_py = files["src/main.py"]
            assert "import" in main_py
            assert "FastAPI" in main_py
            assert service_name in main_py

    async def test_chaos_and_traffic_integration(self, deps):
        """Test chaos engineering and traffic generation integration."""
        simulation_id = "test-sim-123"

        # Test traffic generation
        traffic_pattern = {
            "type": "constant",
            "params": {"users": 10, "duration": "5s", "target_host": "test-service"},
        }

        traffic_job_id = await deps.traffic_generator.start_traffic(simulation_id, traffic_pattern)
        assert traffic_job_id is not None

        # Test chaos injection
        chaos_experiment = {
            "type": "pod-delete",
            "target": {"service": "test-service"},
            "params": {"count": 1},
        }

        experiment_id = await deps.chaos_engine.inject_fault(simulation_id, chaos_experiment)
        assert experiment_id is not None

        # Clean up
        await deps.traffic_generator.stop_traffic(traffic_job_id)
        await deps.chaos_engine.stop_experiment(experiment_id)

    async def test_verification_integration(self, deps):
        """Test verification engine integration."""
        simulation_id = "test-sim-verify"

        # Run verification
        result = await deps.verification_engine.verify_simulation(simulation_id)

        assert "overall_status" in result
        assert "checks" in result
        assert "timestamp" in result

        # Should have multiple check categories
        checks = result["checks"]
        assert len(checks) > 0

    async def test_scenario_management_integration(self, deps):
        """Test scenario management integration."""
        from gong.core.models import Scenario, ScenarioEvent, TrafficPattern

        # Create a test scenario
        scenario = Scenario(
            name="test-scenario",
            description="Test scenario for integration",
            events=[
                ScenarioEvent(
                    timestamp="0s",
                    type="traffic",
                    config=TrafficPattern(
                        name="test-traffic", type="constant", params={"users": 5, "duration": "5s"}
                    ),
                )
            ],
        )

        simulation_id = "test-sim-scenario"

        # Start scenario
        scenario_id = await deps.scenario_manager.start_scenario(simulation_id, scenario)
        assert scenario_id is not None

        # Check scenario status
        import asyncio

        await asyncio.sleep(1)  # Give it time to start

        status = await deps.scenario_manager.get_scenario_status(scenario_id)
        assert status is not None
        assert status["status"] in ["running", "completed"]

        # Stop scenario
        await deps.scenario_manager.stop_scenario(scenario_id)

    async def test_action_execution_integration(self, deps):
        """Test action execution integration."""
        from gong.core.models import ActionRequest

        simulation_id = "test-sim-actions"

        # Test various action types
        actions = [
            ActionRequest(action_type="kubectl_get", params={"resource_type": "pods"}),
            ActionRequest(action_type="kubectl_logs", target="test-service", params={"lines": 10}),
        ]

        for action in actions:
            result = await deps.action_executor.execute_action(simulation_id, action)
            assert result.status in ["COMPLETED", "FAILED"]
            assert result.action_id is not None

    async def test_simulation_lifecycle_integration(self, deps):
        """Test complete simulation lifecycle."""
        from gong.core.models import Simulation

        # 1. Generate config
        spec = await deps.llm_architect.generate_config("Create a test service")

        # 2. Create simulation
        simulation = Simulation(name="lifecycle-test", spec=spec)

        # 3. Save simulation
        await deps.simulation_repo.save_simulation(simulation)

        # 4. Deploy simulation (dummy)
        await deps.orchestrator.deploy_simulation(simulation)

        # 5. Get status
        status = await deps.orchestrator.get_simulation_status(str(simulation.id))
        assert "status" in status

        # 6. Verify simulation
        verification = await deps.verification_engine.verify_simulation(str(simulation.id))
        assert verification["overall_status"] in ["pass", "fail", "partial", "error"]

        # 7. Clean up
        await deps.orchestrator.destroy_simulation(str(simulation.id))
        await deps.simulation_repo.delete_simulation(str(simulation.id))
