"""
Chaos engineering engine implementation.
"""

import random
from typing import Any
from uuid import uuid4

# Import kubernetes before our platform package to avoid naming conflicts
try:
    from kubernetes import client
    from kubernetes.client.rest import ApiException
except ImportError:
    # Fallback if kubernetes is not available
    client = None
    ApiException = Exception

from ..core.interfaces import ChaosEngine


class KubernetesChaosEngine(ChaosEngine):
    """Kubernetes-based chaos engineering engine."""

    def __init__(self) -> None:
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.networking_v1 = client.NetworkingV1Api()
        self.active_experiments: dict[str, dict[str, Any]] = {}

    async def inject_fault(self, simulation_id: str, experiment: dict[str, Any]) -> str:
        """Inject a fault, return experiment ID."""
        experiment_id = str(uuid4())
        namespace = f"sim-{simulation_id[:8]}"

        try:
            if experiment["type"] == "pod-delete":
                await self._inject_pod_delete(namespace, experiment, experiment_id)
            elif experiment["type"] == "network-latency":
                await self._inject_network_latency(namespace, experiment, experiment_id)
            elif experiment["type"] == "cpu-stress":
                await self._inject_cpu_stress(namespace, experiment, experiment_id)
            elif experiment["type"] == "memory-stress":
                await self._inject_memory_stress(namespace, experiment, experiment_id)
            else:
                raise ValueError(f"Unknown experiment type: {experiment['type']}")

            # Store experiment info
            self.active_experiments[experiment_id] = {
                "namespace": namespace,
                "type": experiment["type"],
                "target": experiment.get("target", {}),
                "params": experiment.get("params", {}),
                "status": "running",
            }

            return experiment_id

        except Exception as e:
            raise RuntimeError(f"Failed to inject fault: {e}")

    async def stop_experiment(self, experiment_id: str) -> None:
        """Stop a chaos experiment."""
        if experiment_id not in self.active_experiments:
            return

        experiment = self.active_experiments[experiment_id]

        try:
            if experiment["type"] == "network-latency":
                await self._cleanup_network_latency(experiment)
            elif experiment["type"] in ["cpu-stress", "memory-stress"]:
                await self._cleanup_stress_test(experiment)

            # Mark as stopped
            experiment["status"] = "stopped"

        except Exception:
            # Log error but continue
            pass

    async def _inject_pod_delete(
        self, namespace: str, experiment: dict[str, Any], experiment_id: str
    ) -> None:
        """Inject pod deletion chaos."""
        target = experiment.get("target", {})
        service_name = target.get("service")
        count = experiment.get("params", {}).get("count", 1)

        if not service_name:
            raise ValueError("Pod delete experiment requires target.service")

        # Get pods for the service
        pods = self.v1.list_namespaced_pod(
            namespace=namespace, label_selector=f"app={service_name}"
        )

        if not pods.items:
            raise ValueError(f"No pods found for service {service_name}")

        # Delete random pods
        pods_to_delete = random.sample(pods.items, min(count, len(pods.items)))

        for pod in pods_to_delete:
            try:
                self.v1.delete_namespaced_pod(
                    name=pod.metadata.name, namespace=namespace, grace_period_seconds=0
                )
                # Pod deleted successfully
                pass
            except ApiException:
                # Log error but continue with other pods
                pass

    async def _inject_network_latency(
        self, namespace: str, experiment: dict[str, Any], experiment_id: str
    ) -> None:
        """Inject network latency using network policies."""
        target = experiment.get("target", {})
        service_name = target.get("service")
        experiment.get("params", {}).get("latency", "100ms")

        if not service_name:
            raise ValueError("Network latency experiment requires target.service")

        # Create a network policy that simulates latency
        # Note: This is a simplified implementation
        # In practice, you'd use tools like Istio or Linkerd for traffic shaping
        policy_name = f"chaos-latency-{experiment_id[:8]}"

        network_policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(
                name=policy_name, namespace=namespace, labels={"chaos-experiment": experiment_id}
            ),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(match_labels={"app": service_name}),
                policy_types=["Egress"],
                egress=[
                    client.V1NetworkPolicyEgressRule(
                        to=[client.V1NetworkPolicyPeer()],
                        ports=[client.V1NetworkPolicyPort(port=80)],
                    )
                ],
            ),
        )

        try:
            self.networking_v1.create_namespaced_network_policy(
                namespace=namespace, body=network_policy
            )
        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                raise

    async def _inject_cpu_stress(
        self, namespace: str, experiment: dict[str, Any], experiment_id: str
    ) -> None:
        """Inject CPU stress using a stress-testing pod."""
        target = experiment.get("target", {})
        target.get("service")
        experiment.get("params", {}).get("cpu_load", "50%")
        duration = experiment.get("params", {}).get("duration", "5m")

        stress_pod_name = f"chaos-cpu-stress-{experiment_id[:8]}"

        # Create stress testing pod
        stress_pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=stress_pod_name,
                namespace=namespace,
                labels={"chaos-experiment": experiment_id, "chaos-type": "cpu-stress"},
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="stress",
                        image="progrium/stress",
                        command=["stress"],
                        args=["--cpu", "1", "--timeout", duration, "--verbose"],
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "100m", "memory": "64Mi"},
                            limits={"cpu": "500m", "memory": "128Mi"},
                        ),
                    )
                ],
                restart_policy="Never",
            ),
        )

        try:
            self.v1.create_namespaced_pod(namespace=namespace, body=stress_pod)

        except ApiException as e:
            raise RuntimeError(f"Failed to create stress pod: {e}")

    async def _inject_memory_stress(
        self, namespace: str, experiment: dict[str, Any], experiment_id: str
    ) -> None:
        """Inject memory stress using a stress-testing pod."""
        target = experiment.get("target", {})
        target.get("service")
        memory_size = experiment.get("params", {}).get("memory_size", "100M")
        duration = experiment.get("params", {}).get("duration", "5m")

        stress_pod_name = f"chaos-memory-stress-{experiment_id[:8]}"

        # Create stress testing pod
        stress_pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=stress_pod_name,
                namespace=namespace,
                labels={"chaos-experiment": experiment_id, "chaos-type": "memory-stress"},
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="stress",
                        image="progrium/stress",
                        command=["stress"],
                        args=[
                            "--vm",
                            "1",
                            "--vm-bytes",
                            memory_size,
                            "--timeout",
                            duration,
                            "--verbose",
                        ],
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "100m", "memory": "64Mi"},
                            limits={"cpu": "200m", "memory": "256Mi"},
                        ),
                    )
                ],
                restart_policy="Never",
            ),
        )

        try:
            self.v1.create_namespaced_pod(namespace=namespace, body=stress_pod)

        except ApiException as e:
            raise RuntimeError(f"Failed to create stress pod: {e}")

    async def _cleanup_network_latency(self, experiment: dict[str, Any]) -> None:
        """Clean up network latency experiment."""
        namespace = experiment["namespace"]
        experiment_id = experiment.get("experiment_id")

        try:
            # Delete network policies created by this experiment
            policies = self.networking_v1.list_namespaced_network_policy(
                namespace=namespace, label_selector=f"chaos-experiment={experiment_id}"
            )

            for policy in policies.items:
                self.networking_v1.delete_namespaced_network_policy(
                    name=policy.metadata.name, namespace=namespace
                )

        except ApiException:
            pass

    async def _cleanup_stress_test(self, experiment: dict[str, Any]) -> None:
        """Clean up stress test experiment."""
        namespace = experiment["namespace"]
        experiment_id = experiment.get("experiment_id")

        try:
            # Delete stress testing pods
            pods = self.v1.list_namespaced_pod(
                namespace=namespace, label_selector=f"chaos-experiment={experiment_id}"
            )

            for pod in pods.items:
                self.v1.delete_namespaced_pod(
                    name=pod.metadata.name, namespace=namespace, grace_period_seconds=0
                )

        except ApiException:
            pass


class DummyChaosEngine(ChaosEngine):
    """Dummy chaos engine for development and testing."""

    def __init__(self):
        self.active_experiments: dict[str, dict[str, Any]] = {}

    async def inject_fault(self, simulation_id: str, experiment: dict[str, Any]) -> str:
        """Inject a fault (dummy implementation)."""
        experiment_id = str(uuid4())

        # Store experiment info for tracking

        self.active_experiments[experiment_id] = {
            "simulation_id": simulation_id,
            "type": experiment["type"],
            "status": "running",
        }

        return experiment_id

    async def stop_experiment(self, experiment_id: str) -> None:
        """Stop a chaos experiment (dummy implementation)."""
        if experiment_id in self.active_experiments:
            self.active_experiments[experiment_id]["status"] = "stopped"
            # Experiment stopped successfully
