"""
Kubernetes manifest generator.
"""

from pathlib import Path
from typing import Any

import jinja2

from ..core.models import ServiceDefinition


class KubernetesManifestGenerator:
    """Generate Kubernetes manifests for services."""

    def __init__(self, template_dir: str = None):
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default to k8s templates directory
            self.template_dir = Path(__file__).parent.parent / "templates" / "files" / "k8s"

        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def generate_service_manifests(self, service_def: ServiceDefinition, output_dir: Path):
        """Generate Kubernetes manifests for a service."""

        # Create k8s directory
        k8s_dir = output_dir / "k8s"
        k8s_dir.mkdir(exist_ok=True)

        # Prepare template context
        context = self._prepare_k8s_context(service_def)

        # Generate deployment manifest
        deployment = self._render_template("deployment.yaml.j2", context)
        (k8s_dir / "deployment.yaml").write_text(deployment)

        # Generate service manifest
        service = self._render_template("service.yaml.j2", context)
        (k8s_dir / "service.yaml").write_text(service)

        # Generate configmap manifest
        configmap = self._render_template("configmap.yaml.j2", context)
        (k8s_dir / "configmap.yaml").write_text(configmap)

        # Generate HPA if needed
        if service_def.replicas > 1:
            hpa = self._render_template("hpa.yaml.j2", context)
            (k8s_dir / "hpa.yaml").write_text(hpa)

    def _prepare_k8s_context(self, service_def: ServiceDefinition) -> dict[str, Any]:
        """Prepare context for Kubernetes template rendering."""

        # Extract environment variables from dependencies
        env_vars = []

        # Add service dependencies
        for service_name in service_def.dependencies.get("services", []):
            env_var_name = f"{service_name.upper().replace('-', '_')}_URL"
            env_vars.append({"name": env_var_name, "value": f"http://{service_name}:80"})

        # Add datastore dependencies
        for ds in service_def.dependencies.get("datastores", []):
            if hasattr(ds, "name"):  # DatastoreDependency object
                env_var_name = f"{ds.name.upper().replace('-', '_')}_URL"
                if ds.type == "postgres":
                    env_vars.append(
                        {
                            "name": env_var_name,
                            "value": f"postgresql+asyncpg://postgres:password@{ds.name}:5432/postgres",
                        }
                    )
                elif ds.type == "redis":
                    env_vars.append({"name": env_var_name, "value": f"redis://{ds.name}:6379"})
            elif isinstance(ds, dict):  # Dict format
                env_var_name = f"{ds['name'].upper().replace('-', '_')}_URL"
                if ds["type"] == "postgres":
                    env_vars.append(
                        {
                            "name": env_var_name,
                            "value": f"postgresql+asyncpg://postgres:password@{ds['name']}:5432/postgres",
                        }
                    )
                elif ds["type"] == "redis":
                    env_vars.append({"name": env_var_name, "value": f"redis://{ds['name']}:6379"})

        # Add observability configuration
        env_vars.extend(
            [
                {
                    "name": "LOG_LEVEL",
                    "value": service_def.observability.logging.get("level", "INFO"),
                },
                {"name": "JAEGER_HOST", "value": "jaeger"},
                {"name": "JAEGER_PORT", "value": "14268"},
            ]
        )

        return {
            "service": service_def,
            "service_name": service_def.name,
            "namespace": getattr(service_def, "_namespace", "default"),
            "replicas": service_def.replicas,
            "resources": service_def.resources,
            "env_vars": env_vars,
            "labels": {"app": service_def.name, "version": "v1", "component": "microservice"},
            "ports": [{"name": "http", "port": 8000, "target_port": 8000}],
        }

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a Kubernetes template."""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except jinja2.TemplateNotFound:
            # Return a basic template if not found
            return self._generate_basic_manifest(template_name, context)
        except Exception as e:
            raise ValueError(f"Error rendering template {template_name}: {e}")

    def _generate_basic_manifest(self, template_name: str, context: dict[str, Any]) -> str:
        """Generate basic Kubernetes manifest if template not found."""

        service_name = context["service_name"]
        namespace = context["namespace"]

        if template_name == "deployment.yaml.j2":
            return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service_name}
  namespace: {namespace}
  labels:
    app: {service_name}
spec:
  replicas: {context["replicas"]}
  selector:
    matchLabels:
      app: {service_name}
  template:
    metadata:
      labels:
        app: {service_name}
    spec:
      containers:
      - name: {service_name}
        image: {service_name}:latest
        ports:
        - containerPort: 8000
        env:
{chr(10).join(f"        - name: {env['name']}" + chr(10) + f'          value: "{env["value"]}"' for env in context["env_vars"])}
        resources:
          requests:
            cpu: {context["resources"].requests.cpu}
            memory: {context["resources"].requests.memory}
          limits:
            cpu: {context["resources"].limits.cpu}
            memory: {context["resources"].limits.memory}
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
"""

        elif template_name == "service.yaml.j2":
            return f"""apiVersion: v1
kind: Service
metadata:
  name: {service_name}
  namespace: {namespace}
  labels:
    app: {service_name}
spec:
  selector:
    app: {service_name}
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
"""

        elif template_name == "configmap.yaml.j2":
            return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {service_name}-config
  namespace: {namespace}
  labels:
    app: {service_name}
data:
  SERVICE_NAME: "{service_name}"
  LOG_LEVEL: "INFO"
"""

        elif template_name == "hpa.yaml.j2":
            return f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {service_name}-hpa
  namespace: {namespace}
  labels:
    app: {service_name}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {service_name}
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
"""

        else:
            return f"# Unknown template: {template_name}"
