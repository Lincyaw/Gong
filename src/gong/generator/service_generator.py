"""
Service code generator implementation.
"""

from pathlib import Path

from ..core.interfaces import CodeGenerator, TemplateRegistry
from ..core.models import ServiceDefinition, WorkflowStep


class FastAPIServiceGenerator(CodeGenerator):
    """Generates FastAPI-based microservices."""

    def __init__(self, template_registry: TemplateRegistry):
        self.template_registry = template_registry

    async def generate_service(self, service_def: ServiceDefinition) -> dict[str, str]:
        """Generate complete service code."""
        files = {}

        # Generate main application file
        files["src/main.py"] = await self._generate_main_py(service_def)

        # Generate requirements.txt
        files["requirements.txt"] = self._generate_requirements(service_def)

        # Generate Dockerfile
        files["Dockerfile"] = self._generate_dockerfile()

        # Generate configuration
        files["src/config.py"] = self._generate_config()

        # Generate database utilities if needed
        if self._has_database_dependencies(service_def):
            files["src/database.py"] = self._generate_database_utils()

        return files

    async def generate_and_save_service(
        self, service_def: ServiceDefinition, output_dir: str | None = None
    ) -> dict[str, str]:
        """Generate service code and save to files."""
        # Generate the code
        files = await self.generate_service(service_def)

        # Determine output directory
        if output_dir is None:
            output_dir = f"output/{service_def.name}"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Write files to disk
        for file_path, content in files.items():
            full_path = output_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        print(f"✅ Generated service '{service_def.name}' in {output_path}")
        print("📁 Files created:")
        for file_path in files.keys():
            print(f"   - {output_path / file_path}")

        return files

    async def _generate_main_py(self, service_def: ServiceDefinition) -> str:
        """Generate the main FastAPI application."""
        imports = self._generate_imports(service_def)
        app_init = self._generate_app_initialization(service_def)
        endpoints = await self._generate_endpoints(service_def)

        return f"""
{imports}

{app_init}

{endpoints}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

    def _generate_imports(self, service_def: ServiceDefinition) -> str:
        """Generate import statements."""
        imports = [
            "import asyncio",
            "import os",
            "from typing import Dict, Any",
            "",
            "from fastapi import FastAPI, HTTPException",
            "from fastapi.responses import JSONResponse",
            "import httpx",
        ]

        # Add database imports if needed
        if self._has_database_dependencies(service_def):
            imports.extend(
                [
                    "import asyncpg",
                    "from .database import get_db_connection",
                ]
            )

        # Add observability imports
        imports.extend(
            [
                "",
                "# OpenTelemetry imports",
                "from opentelemetry import trace",
                "from opentelemetry.exporter.jaeger.thrift import JaegerExporter",
                "from opentelemetry.sdk.trace import TracerProvider",
                "from opentelemetry.sdk.trace.export import BatchSpanProcessor",
            ]
        )

        return "\n".join(imports)

    def _generate_app_initialization(self, service_def: ServiceDefinition) -> str:
        """Generate FastAPI app initialization."""
        return f'''
# Initialize FastAPI app
app = FastAPI(
    title="{service_def.name}",
    description="Generated microservice",
    version="1.0.0"
)

# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name=os.getenv("JAEGER_AGENT_HOST", "jaeger"),
    agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {{"status": "healthy", "service": "{service_def.name}"}}
'''

    async def _generate_endpoints(self, service_def: ServiceDefinition) -> str:
        """Generate endpoint handlers."""
        endpoints = []

        for endpoint in service_def.endpoints:
            endpoint_code = await self._generate_endpoint_handler(endpoint, service_def.namespace)
            endpoints.append(endpoint_code)

        return "\n\n".join(endpoints)

    async def _generate_endpoint_handler(self, endpoint, namespace: str) -> str:
        """Generate a single endpoint handler."""
        method = endpoint.method.lower()

        # Generate function signature
        func_name = (
            f"handle_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
        )

        # Generate workflow steps
        workflow_code = await self._generate_workflow_steps(endpoint.workflow, namespace)

        return f'''
@app.{method}("{endpoint.path}")
async def {func_name}(request_data: Dict[str, Any] = None):
    """Generated endpoint handler for {endpoint.path}."""
    with tracer.start_as_current_span("{func_name}"):
        context = {{"request": request_data or {{}}}}

        try:
{workflow_code}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
'''

    async def _generate_workflow_steps(self, workflow: list[WorkflowStep], namespace: str) -> str:
        """Generate code for workflow steps."""
        steps = []

        for step in workflow:
            template = await self.template_registry.get_template(step.template)

            # Add fault injection wrapper if needed
            step_code = template.render(step.params, "context")

            if step.inject_faults:
                step_code = self._wrap_with_fault_injection(step_code, step.inject_faults)

            steps.append(f"            # Step: {step.name}")
            # Properly indent the step code
            indented_step_code = "\n".join(
                f"            {line}" if line.strip() else line for line in step_code.split("\n")
            )
            steps.append(indented_step_code)

        return "\n".join(steps)

    def _wrap_with_fault_injection(self, code: str, faults) -> str:
        """Wrap code with fault injection logic."""
        fault_code = []

        for fault in faults:
            if fault.type == "latency":
                fault_code.append(f"""
            # Inject latency fault
            import random
            if random.random() < {fault.probability}:
                import asyncio
                await asyncio.sleep({fault.value.split("(")[1].split(",")[0]}/1000)  # Convert ms to seconds
""")

        return "\n".join(fault_code) + "\n" + code

    def _generate_requirements(self, service_def: ServiceDefinition) -> str:
        """Generate requirements.txt."""
        requirements = [
            "fastapi==0.104.1",
            "uvicorn==0.24.0",
            "httpx==0.25.2",
            "opentelemetry-api==1.21.0",
            "opentelemetry-sdk==1.21.0",
            "opentelemetry-exporter-jaeger==1.21.0",
            "deprecated>=1.2.14",  # Required by jaeger exporter
        ]

        # Add database dependencies
        if self._has_database_dependencies(service_def):
            requirements.extend(
                [
                    "asyncpg==0.29.0",
                    "sqlalchemy==2.0.23",
                ]
            )

        # Add Redis dependencies
        if self._has_redis_dependencies(service_def):
            requirements.append("redis==5.0.1")

        return "\n".join(requirements)

    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile."""
        return """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["python", "-m", "src.main"]
"""

    def _generate_config(self) -> str:
        """Generate configuration module."""
        return '''
"""
Service configuration.
"""
import os
from typing import Optional

class Config:
    """Service configuration."""

    # Database configuration
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Redis configuration
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # Observability
    JAEGER_AGENT_HOST: str = os.getenv("JAEGER_AGENT_HOST", "jaeger")
    JAEGER_AGENT_PORT: int = int(os.getenv("JAEGER_AGENT_PORT", "6831"))

    # Service discovery
    NAMESPACE: str = os.getenv("NAMESPACE", "default")

config = Config()
'''

    def _generate_database_utils(self) -> str:
        """Generate database utilities."""
        return '''
"""
Database utilities.
"""
import asyncpg
from contextlib import asynccontextmanager
from .config import config

@asynccontextmanager
async def get_db_connection(datastore_name: str = "default"):
    """Get database connection."""
    # In a real implementation, this would use service discovery
    # to find the actual database connection string
    conn = await asyncpg.connect(config.DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()
'''

    def _has_database_dependencies(self, service_def: ServiceDefinition) -> bool:
        """Check if service has database dependencies."""
        datastores = service_def.dependencies.get("datastores", [])
        return any(ds.type in ["postgres", "mysql"] for ds in datastores if hasattr(ds, "type"))

    def _has_redis_dependencies(self, service_def: ServiceDefinition) -> bool:
        """Check if service has Redis dependencies."""
        datastores = service_def.dependencies.get("datastores", [])
        return any(ds.type == "redis" for ds in datastores if hasattr(ds, "type"))
