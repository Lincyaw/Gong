"""
LLM architect for generating simulation configurations.
"""

from ..core.interfaces import LLMArchitect
from ..core.models import ServiceDefinition, ServiceEndpoint, SimulationSpec, WorkflowStep


class DummyLLMArchitect(LLMArchitect):
    """Dummy LLM architect for development."""

    async def generate_config(self, prompt: str) -> SimulationSpec:
        """Generate simulation configuration from natural language prompt."""
        # Dummy implementation - generates a simple e-commerce simulation

        # Parse intent (very basic)
        if "ecommerce" in prompt.lower() or "order" in prompt.lower():
            return self._generate_ecommerce_simulation()
        else:
            return self._generate_basic_simulation()

    async def validate_and_fix_config(
        self, config: SimulationSpec, errors: list[str]
    ) -> SimulationSpec:
        """Validate and fix configuration based on validation errors."""
        # Dummy implementation - just return the original config
        return config

    def _generate_ecommerce_simulation(self) -> SimulationSpec:
        """Generate a basic e-commerce simulation."""

        # User service
        user_service = ServiceDefinition(
            name="user-service",
            replicas=2,
            endpoints=[
                ServiceEndpoint(
                    path="/v1/users/{user_id}",
                    method="GET",
                    workflow=[
                        WorkflowStep(
                            name="get_user_from_db",
                            template="io/postgres_query",
                            params={
                                "datastore_name": "users-db",
                                "query": "SELECT * FROM users WHERE id = $1",
                                "query_params": ["{path.user_id}"],
                            },
                            output="user_data",
                        ),
                        WorkflowStep(
                            name="return_user",
                            template="control_flow/return_response",
                            params={"status_code": 200, "body": "{context.user_data}"},
                        ),
                    ],
                )
            ],
        )

        # Order service
        order_service = ServiceDefinition(
            name="order-service",
            replicas=3,
            dependencies={"services": ["user-service"], "datastores": []},
            endpoints=[
                ServiceEndpoint(
                    path="/v1/orders",
                    method="POST",
                    workflow=[
                        WorkflowStep(
                            name="validate_user",
                            template="io/http_api_call",
                            params={
                                "target_service": "user-service",
                                "path": "/v1/users/{body.user_id}",
                                "method": "GET",
                            },
                            output="user_info",
                        ),
                        WorkflowStep(
                            name="create_order",
                            template="control_flow/return_response",
                            params={
                                "status_code": 201,
                                "body": {
                                    "order_id": "order-123",
                                    "user_id": "{body.user_id}",
                                    "status": "created",
                                },
                            },
                        ),
                    ],
                )
            ],
        )

        return SimulationSpec(
            name="ecommerce-simulation",
            description="Basic e-commerce microservices simulation",
            services=[user_service, order_service],
        )

    def _generate_basic_simulation(self) -> SimulationSpec:
        """Generate a basic simulation."""

        service = ServiceDefinition(
            name="hello-service",
            replicas=1,
            endpoints=[
                ServiceEndpoint(
                    path="/hello",
                    method="GET",
                    workflow=[
                        WorkflowStep(
                            name="return_hello",
                            template="control_flow/return_response",
                            params={"status_code": 200, "body": {"message": "Hello, World!"}},
                        )
                    ],
                )
            ],
        )

        return SimulationSpec(
            name="basic-simulation", description="Basic hello world simulation", services=[service]
        )
