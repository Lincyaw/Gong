"""
Dependency injection for the API layer.
"""

from dataclasses import dataclass

from ..actions.executor import DummyActionExecutor, KubernetesActionExecutor
from ..chaos.engine import DummyChaosEngine, KubernetesChaosEngine
from ..core.interfaces import (
    ActionExecutor,
    ChaosEngine,
    CodeGenerator,
    LLMArchitect,
    Orchestrator,
    SimulationRepository,
    TemplateRegistry,
    TrafficGenerator,
    VerificationEngine,
)
from ..generator.service_generator import ServiceCodeGenerator as FastAPIServiceGenerator
from ..llm.architect import DummyLLMArchitect
from ..orchestrator.k8s_orchestrator import KubernetesOrchestrator
from ..orchestrator.scenario_manager import ScenarioManager
from ..templates.base import InMemoryTemplateRegistry
from ..traffic.generator import DummyTrafficGenerator, LocustTrafficGenerator
from ..utils.repository import InMemorySimulationRepository
from ..verification.engine import DummyVerificationEngine, KubernetesVerificationEngine


@dataclass
class Dependencies:
    """Container for all platform dependencies."""

    template_registry: TemplateRegistry
    code_generator: CodeGenerator
    orchestrator: Orchestrator
    simulation_repo: SimulationRepository
    traffic_generator: TrafficGenerator
    chaos_engine: ChaosEngine
    llm_architect: LLMArchitect
    action_executor: ActionExecutor
    verification_engine: VerificationEngine
    scenario_manager: ScenarioManager


_dependencies: Dependencies | None = None


def get_dependencies() -> Dependencies:
    """Get platform dependencies (singleton)."""
    global _dependencies

    if _dependencies is None:
        # Check if running in Kubernetes
        from ..config import should_use_kubernetes

        use_k8s = should_use_kubernetes()

        # Initialize core dependencies
        template_registry = InMemoryTemplateRegistry()
        code_generator = FastAPIServiceGenerator(None)  # Use default template directory
        simulation_repo = InMemorySimulationRepository()
        llm_architect = DummyLLMArchitect()

        # Initialize environment-specific dependencies
        if use_k8s:
            orchestrator = KubernetesOrchestrator()
            traffic_generator = LocustTrafficGenerator()
            chaos_engine = KubernetesChaosEngine()
            action_executor = KubernetesActionExecutor()
            verification_engine = KubernetesVerificationEngine()
        else:
            # Use dummy implementations for development
            from ..orchestrator.dummy_orchestrator import DummyOrchestrator

            orchestrator = DummyOrchestrator()
            traffic_generator = DummyTrafficGenerator()
            chaos_engine = DummyChaosEngine()
            action_executor = DummyActionExecutor()
            verification_engine = DummyVerificationEngine()

        # Initialize scenario manager
        scenario_manager = ScenarioManager(traffic_generator, chaos_engine)

        _dependencies = Dependencies(
            template_registry=template_registry,
            code_generator=code_generator,
            orchestrator=orchestrator,
            simulation_repo=simulation_repo,
            traffic_generator=traffic_generator,
            chaos_engine=chaos_engine,
            llm_architect=llm_architect,
            action_executor=action_executor,
            verification_engine=verification_engine,
            scenario_manager=scenario_manager,
        )

    return _dependencies
