"""
Kubernetes-based orchestrator implementation.
"""

from typing import Any

from kubernetes import client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from ..core.interfaces import Orchestrator
from ..core.models import Simulation, SimulationStatus


class KubernetesOrchestrator(Orchestrator):
    """Kubernetes-based simulation orchestrator."""

    def __init__(self) -> None:
        # Load Kubernetes configuration
        try:
            k8s_config.load_incluster_config()
        except k8s_config.ConfigException:
            k8s_config.load_kube_config()

        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.networking_v1 = client.NetworkingV1Api()

    async def deploy_simulation(self, simulation: Simulation) -> None:
        """Deploy a simulation to Kubernetes."""
        try:
            # Create namespace
            await self._create_namespace(simulation.namespace)

            # Deploy datastores first
            await self._deploy_datastores(simulation)

            # Deploy services
            await self._deploy_services(simulation)

            # Create network policies
            await self._create_network_policies(simulation)

            simulation.status = SimulationStatus.RUNNING

        except Exception as e:
            simulation.status = SimulationStatus.FAILED
            simulation.error_message = str(e)
            raise

    async def destroy_simulation(self, simulation_id: str) -> None:
        """Destroy a simulation and clean up resources."""
        namespace = f"sim-{simulation_id[:8]}"

        try:
            # Delete namespace (this will delete all resources in it)
            self.v1.delete_namespace(name=namespace)
        except ApiException as e:
            if e.status != 404:  # Ignore if namespace doesn't exist
                raise

    async def get_simulation_status(self, simulation_id: str) -> dict[str, Any]:
        """Get current status and topology of a simulation."""
        namespace = f"sim-{simulation_id[:8]}"

        try:
            # Get pods
            pods = self.v1.list_namespaced_pod(namespace=namespace)

            # Get services
            services = self.v1.list_namespaced_service(namespace=namespace)

            # Get deployments
            deployments = self.apps_v1.list_namespaced_deployment(namespace=namespace)

            return {
                "namespace": namespace,
                "pods": [self._pod_to_dict(pod) for pod in pods.items],
                "services": [self._service_to_dict(svc) for svc in services.items],
                "deployments": [self._deployment_to_dict(dep) for dep in deployments.items],
            }

        except ApiException as e:
            if e.status == 404:
                return {"error": "Simulation not found"}
            raise

    async def _create_namespace(self, namespace: str) -> None:
        """Create Kubernetes namespace."""
        ns_manifest = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace, labels={"managed-by": "simulation-platform"}
            )
        )

        try:
            self.v1.create_namespace(body=ns_manifest)
        except ApiException as e:
            if e.status != 409:  # Ignore if namespace already exists
                raise

    async def _deploy_datastores(self, simulation: Simulation) -> None:
        """Deploy datastore dependencies."""
        for service_def in simulation.spec.services:
            datastores = service_def.dependencies.get("datastores", [])

            for datastore in datastores:
                if hasattr(datastore, "provisioning") and datastore.provisioning.mode == "dynamic":
                    await self._deploy_datastore(simulation.namespace, datastore)

    async def _deploy_datastore(self, namespace: str, datastore) -> None:
        """Deploy a single datastore."""
        if datastore.type == "postgres":
            await self._deploy_postgres(namespace, datastore.name)
        elif datastore.type == "redis":
            await self._deploy_redis(namespace, datastore.name)

    async def _deploy_postgres(self, namespace: str, name: str) -> None:
        """Deploy PostgreSQL instance."""
        # Create ConfigMap for initialization
        config_map = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=f"{name}-config", namespace=namespace),
            data={"init.sql": "-- Database initialization"},
        )
        self.v1.create_namespaced_config_map(namespace=namespace, body=config_map)

        # Create Secret for credentials
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=f"{name}-secret", namespace=namespace),
            string_data={
                "POSTGRES_DB": "appdb",
                "POSTGRES_USER": "appuser",
                "POSTGRES_PASSWORD": "generated-password-123",
            },
        )
        self.v1.create_namespaced_secret(namespace=namespace, body=secret)

        # Create Deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": name}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="postgres",
                                image="postgres:14",
                                env_from=[
                                    client.V1EnvFromSource(
                                        secret_ref=client.V1SecretEnvSource(name=f"{name}-secret")
                                    )
                                ],
                                ports=[client.V1ContainerPort(container_port=5432)],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name="init-sql", mount_path="/docker-entrypoint-initdb.d"
                                    )
                                ],
                            )
                        ],
                        volumes=[
                            client.V1Volume(
                                name="init-sql",
                                config_map=client.V1ConfigMapVolumeSource(name=f"{name}-config"),
                            )
                        ],
                    ),
                ),
            ),
        )
        self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)

        # Create Service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1ServiceSpec(
                selector={"app": name}, ports=[client.V1ServicePort(port=5432, target_port=5432)]
            ),
        )
        self.v1.create_namespaced_service(namespace=namespace, body=service)

    async def _deploy_redis(self, namespace: str, name: str) -> None:
        """Deploy Redis instance."""
        # Create Deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": name}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="redis",
                                image="redis:6",
                                ports=[client.V1ContainerPort(container_port=6379)],
                            )
                        ]
                    ),
                ),
            ),
        )
        self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)

        # Create Service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=name, namespace=namespace),
            spec=client.V1ServiceSpec(
                selector={"app": name}, ports=[client.V1ServicePort(port=6379, target_port=6379)]
            ),
        )
        self.v1.create_namespaced_service(namespace=namespace, body=service)

    async def _deploy_services(self, simulation: Simulation) -> None:
        """Deploy application services."""
        for service_def in simulation.spec.services:
            await self._deploy_service(simulation.namespace, service_def)

    async def _deploy_service(self, namespace: str, service_def) -> None:
        """Deploy a single application service."""
        # Create Deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=service_def.name, namespace=namespace),
            spec=client.V1DeploymentSpec(
                replicas=service_def.replicas,
                selector=client.V1LabelSelector(match_labels={"app": service_def.name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": service_def.name}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name=service_def.name,
                                image=f"simulation-platform/{service_def.name}:latest",
                                ports=[client.V1ContainerPort(container_port=8000)],
                                env=[client.V1EnvVar(name="NAMESPACE", value=namespace)],
                                resources=client.V1ResourceRequirements(
                                    requests={
                                        "cpu": service_def.resources.requests.cpu,
                                        "memory": service_def.resources.requests.memory,
                                    },
                                    limits={
                                        "cpu": service_def.resources.limits.cpu,
                                        "memory": service_def.resources.limits.memory,
                                    },
                                ),
                            )
                        ]
                    ),
                ),
            ),
        )
        self.apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)

        # Create Service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=service_def.name, namespace=namespace),
            spec=client.V1ServiceSpec(
                selector={"app": service_def.name},
                ports=[client.V1ServicePort(port=80, target_port=8000)],
            ),
        )
        self.v1.create_namespaced_service(namespace=namespace, body=service)

    async def _create_network_policies(self, simulation: Simulation) -> None:
        """Create network policies for isolation."""
        # Create default deny-all policy
        deny_all_policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(name="deny-all", namespace=simulation.namespace),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(), policy_types=["Ingress", "Egress"]
            ),
        )

        try:
            self.networking_v1.create_namespaced_network_policy(
                namespace=simulation.namespace, body=deny_all_policy
            )
        except ApiException as e:
            if e.status != 409:  # Ignore if already exists
                raise

    def _pod_to_dict(self, pod: client.V1Pod) -> dict[str, Any]:
        """Convert Pod to dictionary."""
        return {
            "name": pod.metadata.name,
            "status": pod.status.phase,
            "ready": all(
                condition.status == "True"
                for condition in (pod.status.conditions or [])
                if condition.type == "Ready"
            ),
        }

    def _service_to_dict(self, service: client.V1Service) -> dict[str, Any]:
        """Convert Service to dictionary."""
        return {
            "name": service.metadata.name,
            "type": service.spec.type,
            "ports": [
                {"port": port.port, "target_port": port.target_port} for port in service.spec.ports
            ],
        }

    def _deployment_to_dict(self, deployment: client.V1Deployment) -> dict[str, Any]:
        """Convert Deployment to dictionary."""
        return {
            "name": deployment.metadata.name,
            "replicas": deployment.spec.replicas,
            "ready_replicas": deployment.status.ready_replicas or 0,
            "available_replicas": deployment.status.available_replicas or 0,
        }
