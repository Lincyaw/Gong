"""
Action executor for LLM Agent interactions.
"""

import asyncio
from datetime import datetime
from typing import Any

from kubernetes import client
from kubernetes.client.rest import ApiException

from ..core.interfaces import ActionExecutor
from ..core.models import ActionRequest, ActionResult


class KubernetesActionExecutor(ActionExecutor):
    """Kubernetes-based action executor for LLM agents."""

    def __init__(self) -> None:
        self.running_actions: dict[str, dict[str, Any]] = {}
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    async def execute_action(self, simulation_id: str, action: ActionRequest) -> ActionResult:
        """Execute an action in the specified simulation."""
        namespace = f"sim-{simulation_id[:8]}"

        try:
            if action.action_type == "kubectl_logs":
                return await self._execute_kubectl_logs(namespace, action)
            elif action.action_type == "kubectl_describe":
                return await self._execute_kubectl_describe(namespace, action)
            elif action.action_type == "kubectl_get":
                return await self._execute_kubectl_get(namespace, action)
            elif action.action_type == "kubectl_exec":
                return await self._execute_kubectl_exec(namespace, action)
            elif action.action_type == "kubectl_rollout":
                return await self._execute_kubectl_rollout(namespace, action)
            elif action.action_type == "get_metrics":
                return await self._execute_get_metrics(namespace, action)
            elif action.action_type == "get_topology":
                return await self._execute_get_topology(namespace, action)
            elif action.action_type == "diagnose_service":
                return await self._execute_diagnose_service(namespace, action)
            else:
                return ActionResult(
                    status="FAILED", error=f"Unknown action type: {action.action_type}"
                )

        except Exception as e:
            return ActionResult(status="FAILED", error=str(e))

    async def _execute_kubectl_logs(self, namespace: str, action: ActionRequest) -> ActionResult:
        """Execute kubectl logs command."""
        target = action.target or action.params.get("target")
        lines = action.params.get("lines", 100)
        action.params.get("follow", False)

        if not target:
            return ActionResult(status="FAILED", error="Target pod/deployment name is required")

        try:
            # Get logs from pods
            if target.startswith("deployment/"):
                deployment_name = target.replace("deployment/", "")
                pods = self.v1.list_namespaced_pod(
                    namespace=namespace, label_selector=f"app={deployment_name}"
                )

                if not pods.items:
                    return ActionResult(
                        status="FAILED", error=f"No pods found for deployment {deployment_name}"
                    )

                # Get logs from first pod
                pod_name = pods.items[0].metadata.name
            else:
                pod_name = target

            # Get logs
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name, namespace=namespace, tail_lines=lines
            )

            return ActionResult(
                status="COMPLETED",
                result={"pod": pod_name, "logs": logs, "lines": len(logs.split("\n"))},
            )

        except ApiException as e:
            return ActionResult(status="FAILED", error=f"Kubernetes API error: {e}")

    async def _execute_kubectl_describe(
        self, namespace: str, action: ActionRequest
    ) -> ActionResult:
        """Execute kubectl describe command."""
        target = action.target or action.params.get("target")

        if not target:
            return ActionResult(status="FAILED", error="Target resource is required")

        try:
            if target.startswith("pod/"):
                pod_name = target.replace("pod/", "")
                pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)

                # Convert pod to dict for JSON serialization
                pod_dict = pod.to_dict()

                return ActionResult(
                    status="COMPLETED",
                    result={"resource_type": "pod", "name": pod_name, "details": pod_dict},
                )

            elif target.startswith("deployment/"):
                deployment_name = target.replace("deployment/", "")
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name, namespace=namespace
                )

                return ActionResult(
                    status="COMPLETED",
                    result={
                        "resource_type": "deployment",
                        "name": deployment_name,
                        "details": deployment.to_dict(),
                    },
                )

            else:
                return ActionResult(
                    status="FAILED", error=f"Unsupported resource type in target: {target}"
                )

        except ApiException as e:
            return ActionResult(status="FAILED", error=f"Kubernetes API error: {e}")

    async def _execute_kubectl_get(self, namespace: str, action: ActionRequest) -> ActionResult:
        """Execute kubectl get command."""
        resource_type = action.params.get("resource_type", "pods")

        try:
            if resource_type == "pods":
                pods = self.v1.list_namespaced_pod(namespace=namespace)
                result = []

                for pod in pods.items:
                    result.append(
                        {
                            "name": pod.metadata.name,
                            "status": pod.status.phase,
                            "ready": self._is_pod_ready(pod),
                            "restarts": sum(
                                container.restart_count or 0
                                for container in (pod.status.container_statuses or [])
                            ),
                            "age": self._calculate_age(pod.metadata.creation_timestamp),
                        }
                    )

                return ActionResult(
                    status="COMPLETED", result={"resource_type": "pods", "items": result}
                )

            elif resource_type == "services":
                services = self.v1.list_namespaced_service(namespace=namespace)
                result = []

                for service in services.items:
                    result.append(
                        {
                            "name": service.metadata.name,
                            "type": service.spec.type,
                            "cluster_ip": service.spec.cluster_ip,
                            "ports": [
                                {"port": port.port, "target_port": port.target_port}
                                for port in service.spec.ports
                            ],
                            "age": self._calculate_age(service.metadata.creation_timestamp),
                        }
                    )

                return ActionResult(
                    status="COMPLETED", result={"resource_type": "services", "items": result}
                )

            elif resource_type == "deployments":
                deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)
                result = []

                for deployment in deployments.items:
                    result.append(
                        {
                            "name": deployment.metadata.name,
                            "ready": f"{deployment.status.ready_replicas or 0}/{deployment.spec.replicas}",
                            "up_to_date": deployment.status.updated_replicas or 0,
                            "available": deployment.status.available_replicas or 0,
                            "age": self._calculate_age(deployment.metadata.creation_timestamp),
                        }
                    )

                return ActionResult(
                    status="COMPLETED", result={"resource_type": "deployments", "items": result}
                )

            else:
                return ActionResult(
                    status="FAILED", error=f"Unsupported resource type: {resource_type}"
                )

        except ApiException as e:
            return ActionResult(status="FAILED", error=f"Kubernetes API error: {e}")

    async def _execute_kubectl_exec(self, namespace: str, action: ActionRequest) -> ActionResult:
        """Execute kubectl exec command."""
        target = action.target or action.params.get("target")
        command = action.params.get("command", ["sh", "-c", "echo 'Hello from pod'"])

        if not target:
            return ActionResult(status="FAILED", error="Target pod name is required")

        try:
            # For security, limit allowed commands
            allowed_commands = [
                "ps",
                "top",
                "df",
                "free",
                "netstat",
                "ss",
                "curl",
                "wget",
                "cat",
                "ls",
                "pwd",
                "whoami",
                "date",
                "uptime",
            ]

            if isinstance(command, list) and command:
                base_command = command[0]
            elif isinstance(command, str):
                base_command = command.split()[0]
            else:
                base_command = ""

            if base_command not in allowed_commands:
                return ActionResult(
                    status="FAILED",
                    error=f"Command '{base_command}' is not allowed for security reasons",
                )

            # In a real implementation, you would use the Kubernetes exec API
            # For now, we'll simulate the execution
            return ActionResult(
                status="COMPLETED",
                result={
                    "pod": target,
                    "command": command,
                    "output": f"Simulated output from command: {command}",
                    "exit_code": 0,
                },
            )

        except Exception as e:
            return ActionResult(status="FAILED", error=str(e))

    async def _execute_kubectl_rollout(self, namespace: str, action: ActionRequest) -> ActionResult:
        """Execute kubectl rollout command."""
        target = action.target or action.params.get("target")
        operation = action.params.get("operation", "restart")

        if not target:
            return ActionResult(status="FAILED", error="Target deployment is required")

        try:
            deployment_name = target.replace("deployment/", "")

            if operation == "restart":
                # Trigger a rolling restart by updating an annotation
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name, namespace=namespace
                )

                # Add restart annotation
                if not deployment.spec.template.metadata.annotations:
                    deployment.spec.template.metadata.annotations = {}

                deployment.spec.template.metadata.annotations[
                    "kubectl.kubernetes.io/restartedAt"
                ] = datetime.utcnow().isoformat()

                # Update deployment
                self.apps_v1.patch_namespaced_deployment(
                    name=deployment_name, namespace=namespace, body=deployment
                )

                return ActionResult(
                    status="COMPLETED",
                    result={
                        "deployment": deployment_name,
                        "operation": "restart",
                        "message": f"Deployment {deployment_name} restarted",
                    },
                )

            else:
                return ActionResult(
                    status="FAILED", error=f"Unsupported rollout operation: {operation}"
                )

        except ApiException as e:
            return ActionResult(status="FAILED", error=f"Kubernetes API error: {e}")

    async def _execute_get_metrics(self, namespace: str, action: ActionRequest) -> ActionResult:
        """Get metrics for the simulation."""
        service = action.params.get("service")
        action.params.get("metric_type", "all")

        # In a real implementation, you would query Prometheus
        # For now, we'll simulate metrics
        metrics = {
            "cpu_usage": {"value": 45.2, "unit": "percent"},
            "memory_usage": {"value": 67.8, "unit": "percent"},
            "request_rate": {"value": 125.5, "unit": "requests/sec"},
            "error_rate": {"value": 2.1, "unit": "percent"},
            "response_time": {"value": 245.3, "unit": "ms"},
        }

        if service:
            metrics["service"] = service

        return ActionResult(
            status="COMPLETED",
            result={
                "namespace": namespace,
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _execute_get_topology(self, namespace: str, action: ActionRequest) -> ActionResult:
        """Get service topology for the simulation."""
        try:
            # Get services and their relationships
            services = self.v1.list_namespaced_service(namespace=namespace)
            deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)

            topology = {"services": [], "dependencies": []}

            for service in services.items:
                topology["services"].append(
                    {"name": service.metadata.name, "type": "service", "status": "running"}
                )

            for deployment in deployments.items:
                topology["services"].append(
                    {
                        "name": deployment.metadata.name,
                        "type": "deployment",
                        "replicas": deployment.spec.replicas,
                        "ready_replicas": deployment.status.ready_replicas or 0,
                        "status": "running"
                        if deployment.status.ready_replicas == deployment.spec.replicas
                        else "degraded",
                    }
                )

            return ActionResult(
                status="COMPLETED", result={"namespace": namespace, "topology": topology}
            )

        except ApiException as e:
            return ActionResult(status="FAILED", error=f"Kubernetes API error: {e}")

    async def _execute_diagnose_service(
        self, namespace: str, action: ActionRequest
    ) -> ActionResult:
        """Diagnose a specific service."""
        service_name = action.target or action.params.get("service")

        if not service_name:
            return ActionResult(status="FAILED", error="Service name is required")

        try:
            diagnosis = {"service": service_name, "checks": []}

            # Check if service exists
            try:
                self.v1.read_namespaced_service(name=service_name, namespace=namespace)
                diagnosis["checks"].append(
                    {"check": "service_exists", "status": "pass", "message": "Service exists"}
                )
            except ApiException:
                diagnosis["checks"].append(
                    {"check": "service_exists", "status": "fail", "message": "Service not found"}
                )

                return ActionResult(status="COMPLETED", result=diagnosis)

            # Check if deployment exists
            try:
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=service_name, namespace=namespace
                )
                diagnosis["checks"].append(
                    {"check": "deployment_exists", "status": "pass", "message": "Deployment exists"}
                )

                # Check deployment health
                ready_replicas = deployment.status.ready_replicas or 0
                desired_replicas = deployment.spec.replicas

                if ready_replicas == desired_replicas:
                    diagnosis["checks"].append(
                        {
                            "check": "deployment_health",
                            "status": "pass",
                            "message": f"All {desired_replicas} replicas are ready",
                        }
                    )
                else:
                    diagnosis["checks"].append(
                        {
                            "check": "deployment_health",
                            "status": "fail",
                            "message": f"Only {ready_replicas}/{desired_replicas} replicas are ready",
                        }
                    )

            except ApiException:
                diagnosis["checks"].append(
                    {
                        "check": "deployment_exists",
                        "status": "fail",
                        "message": "Deployment not found",
                    }
                )

            # Check pods
            pods = self.v1.list_namespaced_pod(
                namespace=namespace, label_selector=f"app={service_name}"
            )

            if pods.items:
                healthy_pods = sum(1 for pod in pods.items if self._is_pod_ready(pod))
                diagnosis["checks"].append(
                    {
                        "check": "pod_health",
                        "status": "pass" if healthy_pods == len(pods.items) else "fail",
                        "message": f"{healthy_pods}/{len(pods.items)} pods are healthy",
                    }
                )
            else:
                diagnosis["checks"].append(
                    {"check": "pod_health", "status": "fail", "message": "No pods found"}
                )

            return ActionResult(status="COMPLETED", result=diagnosis)

        except Exception as e:
            return ActionResult(status="FAILED", error=str(e))

    def _is_pod_ready(self, pod) -> bool:
        """Check if a pod is ready."""
        if not pod.status.conditions:
            return False

        for condition in pod.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                return True

        return False

    def _calculate_age(self, creation_timestamp) -> str:
        """Calculate age of a resource."""
        if not creation_timestamp:
            return "unknown"

        age = datetime.utcnow().replace(tzinfo=None) - creation_timestamp.replace(tzinfo=None)

        if age.days > 0:
            return f"{age.days}d"
        elif age.seconds > 3600:
            return f"{age.seconds // 3600}h"
        elif age.seconds > 60:
            return f"{age.seconds // 60}m"
        else:
            return f"{age.seconds}s"


class DummyActionExecutor(ActionExecutor):
    """Dummy action executor for development."""

    async def execute_action(self, simulation_id: str, action: ActionRequest) -> ActionResult:
        """Execute an action (dummy implementation)."""
        print(f"🎯 Executing action '{action.action_type}' on {action.target or 'simulation'}")

        # Simulate execution delay
        await asyncio.sleep(1)

        # Generate dummy results based on action type
        if action.action_type == "kubectl_logs":
            result = {
                "logs": "2024-01-15 10:30:00 INFO Starting application\n2024-01-15 10:30:01 INFO Server listening on port 8000",
                "lines": 2,
            }
        elif action.action_type == "kubectl_get":
            result = {
                "resource_type": action.params.get("resource_type", "pods"),
                "items": [
                    {"name": "service-pod-1", "status": "Running", "ready": True},
                    {"name": "service-pod-2", "status": "Running", "ready": True},
                ],
            }
        elif action.action_type == "get_metrics":
            result = {
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "request_rate": 125.5,
                "error_rate": 2.1,
            }
        else:
            result = f"Executed {action.action_type} successfully"

        return ActionResult(status="COMPLETED", result=result)
