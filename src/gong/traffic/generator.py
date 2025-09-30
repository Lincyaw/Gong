"""
Traffic generation engine implementation.
"""

import asyncio
import random
from typing import Any
from uuid import uuid4

import httpx
from kubernetes import client
from kubernetes.client.rest import ApiException

from ..core.interfaces import TrafficGenerator


class LocustTrafficGenerator(TrafficGenerator):
    """Locust-based traffic generator."""

    def __init__(self):
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.active_jobs: dict[str, dict[str, Any]] = {}

    async def start_traffic(self, simulation_id: str, pattern: dict[str, Any]) -> str:
        """Start traffic generation using Locust."""
        job_id = str(uuid4())
        namespace = f"sim-{simulation_id[:8]}"

        try:
            # Create ConfigMap with Locust script
            locust_script = self._generate_locust_script(pattern)
            config_map = self._create_locust_config_map(job_id, namespace, locust_script)
            self.v1.create_namespaced_config_map(namespace=namespace, body=config_map)

            # Create Locust deployment
            deployment = self._create_locust_deployment(job_id, namespace, pattern)
            self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)

            # Store job info
            self.active_jobs[job_id] = {
                "simulation_id": simulation_id,
                "namespace": namespace,
                "pattern": pattern,
                "status": "running",
            }

            print(f"Started traffic generation job {job_id} for simulation {simulation_id}")
            return job_id

        except Exception as e:
            raise RuntimeError(f"Failed to start traffic generation: {e}")

    async def stop_traffic(self, traffic_job_id: str) -> None:
        """Stop traffic generation."""
        if traffic_job_id not in self.active_jobs:
            return

        job_info = self.active_jobs[traffic_job_id]
        namespace = job_info["namespace"]

        try:
            # Delete Locust deployment
            deployment_name = f"locust-{traffic_job_id[:8]}"
            self.apps_v1.delete_namespaced_deployment(name=deployment_name, namespace=namespace)

            # Delete ConfigMap
            config_map_name = f"locust-script-{traffic_job_id[:8]}"
            self.v1.delete_namespaced_config_map(name=config_map_name, namespace=namespace)

            # Update status
            job_info["status"] = "stopped"
            print(f"Stopped traffic generation job {traffic_job_id}")

        except ApiException as e:
            if e.status != 404:  # Ignore if not found
                pass

    def _generate_locust_script(self, pattern: dict[str, Any]) -> str:
        """Generate Locust script based on traffic pattern."""
        pattern_type = pattern.get("type", "constant")
        params = pattern.get("params", {})
        target_host = params.get("target_host", "order-service")

        if pattern_type == "constant":
            params.get("users", 10)
            params.get("spawn_rate", 1)

            script = f"""
from locust import HttpUser, task, between
import random

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://{target_host}"

    @task(3)
    def view_products(self):
        product_id = random.randint(1, 100)
        self.client.get(f"/v1/products/{{product_id}}")

    @task(2)
    def view_user(self):
        user_id = random.randint(1, 50)
        self.client.get(f"/v1/users/{{user_id}}")

    @task(1)
    def create_order(self):
        order_data = {{
            "userId": random.randint(1, 50),
            "productId": random.randint(1, 100),
            "quantity": random.randint(1, 5)
        }}
        self.client.post("/v1/orders", json=order_data)
"""

        elif pattern_type == "ramp":
            params.get("start_users", 1)
            params.get("end_users", 100)
            params.get("duration", "10m")

            script = f"""
from locust import HttpUser, task, between
import random

class WebsiteUser(HttpUser):
    wait_time = between(1, 2)
    host = "http://{target_host}"

    @task(3)
    def view_products(self):
        product_id = random.randint(1, 100)
        self.client.get(f"/v1/products/{{product_id}}")

    @task(2)
    def view_user(self):
        user_id = random.randint(1, 50)
        self.client.get(f"/v1/users/{{user_id}}")

    @task(1)
    def create_order(self):
        order_data = {{
            "userId": random.randint(1, 50),
            "productId": random.randint(1, 100),
            "quantity": random.randint(1, 5)
        }}
        self.client.post("/v1/orders", json=order_data)
"""

        elif pattern_type == "spike":
            params.get("users", 500)
            params.get("duration", "5m")

            script = f"""
from locust import HttpUser, task, between
import random

class WebsiteUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Faster requests for spike
    host = "http://{target_host}"

    @task(5)
    def create_order(self):
        order_data = {{
            "userId": random.randint(1, 50),
            "productId": random.randint(1, 100),
            "quantity": random.randint(1, 5)
        }}
        self.client.post("/v1/orders", json=order_data)

    @task(2)
    def view_products(self):
        product_id = random.randint(1, 100)
        self.client.get(f"/v1/products/{{product_id}}")
"""

        else:
            # Default script
            script = f"""
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://{target_host}"

    @task
    def health_check(self):
        self.client.get("/health")
"""

        return script

    def _create_locust_config_map(
        self, job_id: str, namespace: str, script: str
    ) -> client.V1ConfigMap:
        """Create ConfigMap with Locust script."""
        config_map_name = f"locust-script-{job_id[:8]}"

        return client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=config_map_name, namespace=namespace, labels={"traffic-job": job_id}
            ),
            data={"locustfile.py": script},
        )

    def _create_locust_deployment(
        self, job_id: str, namespace: str, pattern: dict[str, Any]
    ) -> client.V1Deployment:
        """Create Locust deployment."""
        deployment_name = f"locust-{job_id[:8]}"
        params = pattern.get("params", {})

        # Determine Locust command based on pattern
        users = params.get("users", 10)
        spawn_rate = params.get("spawn_rate", 1)

        return client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=deployment_name, namespace=namespace, labels={"traffic-job": job_id}
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": deployment_name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": deployment_name, "traffic-job": job_id}
                    ),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="locust",
                                image="locustio/locust:2.17.0",
                                command=["locust"],
                                args=[
                                    "--locustfile",
                                    "/mnt/locust/locustfile.py",
                                    "--headless",
                                    "--users",
                                    str(users),
                                    "--spawn-rate",
                                    str(spawn_rate),
                                    "--run-time",
                                    params.get("duration", "10m"),
                                    "--html",
                                    "/tmp/report.html",
                                ],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name="locust-script", mount_path="/mnt/locust"
                                    )
                                ],
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": "100m", "memory": "128Mi"},
                                    limits={"cpu": "500m", "memory": "512Mi"},
                                ),
                            )
                        ],
                        volumes=[
                            client.V1Volume(
                                name="locust-script",
                                config_map=client.V1ConfigMapVolumeSource(
                                    name=f"locust-script-{job_id[:8]}"
                                ),
                            )
                        ],
                    ),
                ),
            ),
        )


class DummyTrafficGenerator(TrafficGenerator):
    """Dummy traffic generator for development and testing."""

    def __init__(self):
        self.active_jobs: dict[str, dict[str, Any]] = {}

    async def start_traffic(self, simulation_id: str, pattern: dict[str, Any]) -> str:
        """Start traffic generation (dummy implementation)."""
        job_id = str(uuid4())

        print(f"🚦 Starting traffic generation for simulation {simulation_id}")
        print(f"   Pattern: {pattern.get('type', 'unknown')}")
        print(f"   Params: {pattern.get('params', {})}")

        self.active_jobs[job_id] = {
            "simulation_id": simulation_id,
            "pattern": pattern,
            "status": "running",
        }

        # Simulate some traffic generation
        asyncio.create_task(self._simulate_traffic(job_id, pattern))

        return job_id

    async def stop_traffic(self, traffic_job_id: str) -> None:
        """Stop traffic generation (dummy implementation)."""
        if traffic_job_id in self.active_jobs:
            self.active_jobs[traffic_job_id]["status"] = "stopped"
            print(f"🛑 Stopped traffic generation job {traffic_job_id}")

    async def _simulate_traffic(self, job_id: str, pattern: dict[str, Any]) -> None:
        """Simulate traffic generation with dummy HTTP requests."""
        if job_id not in self.active_jobs:
            return

        job_info = self.active_jobs[job_id]
        params = pattern.get("params", {})
        target_host = params.get("target_host", "localhost:8000")
        users = params.get("users", 10)
        duration_str = params.get("duration", "30s")

        # Parse duration (simple implementation)
        if duration_str.endswith("s"):
            duration = int(duration_str[:-1])
        elif duration_str.endswith("m"):
            duration = int(duration_str[:-1]) * 60
        else:
            duration = 30

        print(f"   Simulating {users} users for {duration} seconds")

        # Simulate requests
        start_time = asyncio.get_event_loop().time()
        request_count = 0

        async with httpx.AsyncClient() as client:
            while (asyncio.get_event_loop().time() - start_time) < duration:
                if job_info["status"] != "running":
                    break

                try:
                    # Simulate different types of requests
                    endpoints = ["/health", "/v1/users/1", "/v1/products/1"]
                    endpoint = random.choice(endpoints)

                    await client.get(f"http://{target_host}{endpoint}", timeout=5.0)
                    request_count += 1

                    if request_count % 10 == 0:
                        print(f"   Generated {request_count} requests...")

                except Exception:
                    # Ignore connection errors in dummy mode
                    pass

                # Wait between requests
                await asyncio.sleep(1.0 / users)  # Distribute load

        print(f"   Traffic simulation completed: {request_count} requests generated")
        job_info["status"] = "completed"
