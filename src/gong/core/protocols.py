"""
Modern Python protocols and type definitions using latest typing features.
"""

from __future__ import annotations

from collections.abc import Awaitable, Mapping, Sequence
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

# Type variables for generic protocols
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


@runtime_checkable
class Serializable(Protocol):
    """Protocol for objects that can be serialized to dict."""

    def to_dict(self) -> dict[str, Any]:
        """Convert object to dictionary representation."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Serializable:
        """Create object from dictionary representation."""
        ...


@runtime_checkable
class AsyncRepository(Protocol, Generic[T]):
    """Generic async repository protocol."""

    async def save(self, entity: T) -> None:
        """Save entity to repository."""
        ...

    async def get(self, id: str) -> T | None:
        """Get entity by ID."""
        ...

    async def list(self) -> Sequence[T]:
        """List all entities."""
        ...

    async def delete(self, id: str) -> None:
        """Delete entity by ID."""
        ...


@runtime_checkable
class ConfigProvider(Protocol):
    """Protocol for configuration providers."""

    def get(self, key: str, default: T | None = None) -> T | None:
        """Get configuration value."""
        ...

    def get_required(self, key: str) -> Any:
        """Get required configuration value, raise if missing."""
        ...

    def get_all(self) -> Mapping[str, Any]:
        """Get all configuration values."""
        ...


@runtime_checkable
class TemplateRenderer(Protocol):
    """Protocol for template rendering engines."""

    def render(self, template: str, context: Mapping[str, Any]) -> str:
        """Render template with context."""
        ...

    def render_file(self, template_path: str, context: Mapping[str, Any]) -> str:
        """Render template file with context."""
        ...


@runtime_checkable
class AsyncEventHandler(Protocol):
    """Protocol for async event handlers."""

    async def handle(self, event: Any) -> None:
        """Handle an event."""
        ...

    def can_handle(self, event: Any) -> bool:
        """Check if this handler can handle the event."""
        ...


@runtime_checkable
class ResourceManager(Protocol):
    """Protocol for managing resources with lifecycle."""

    async def create(self, spec: dict[str, Any]) -> str:
        """Create a resource and return its ID."""
        ...

    async def update(self, id: str, spec: dict[str, Any]) -> None:
        """Update a resource."""
        ...

    async def delete(self, id: str) -> None:
        """Delete a resource."""
        ...

    async def get_status(self, id: str) -> dict[str, Any]:
        """Get resource status."""
        ...


@runtime_checkable
class AsyncContextManager(Protocol):
    """Protocol for async context managers."""

    async def __aenter__(self) -> Any:
        """Enter async context."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context."""
        ...


@runtime_checkable
class HealthCheckable(Protocol):
    """Protocol for components that can report health status."""

    async def health_check(self) -> dict[str, Any]:
        """Perform health check and return status."""
        ...

    def is_healthy(self) -> bool:
        """Quick health status check."""
        ...


@runtime_checkable
class Metrics(Protocol):
    """Protocol for metrics collection."""

    def counter(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None) -> None:
        """Record a counter metric."""
        ...

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a gauge metric."""
        ...

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a histogram metric."""
        ...


# Modern union types and generic aliases
JsonValue = str | int | float | bool | None | dict[str, Any] | list[Any]
Headers = dict[str, str]
QueryParams = dict[str, str | list[str]]


# Generic result type for operations that can fail
class Result(Generic[T]):
    """Result type for operations that can succeed or fail."""

    def __init__(self, value: T | None = None, error: Exception | None = None):
        self._value = value
        self._error = error

    @property
    def is_success(self) -> bool:
        """Check if result is successful."""
        return self._error is None

    @property
    def is_error(self) -> bool:
        """Check if result is an error."""
        return self._error is not None

    @property
    def value(self) -> T:
        """Get the value, raise if error."""
        if self._error:
            raise self._error
        if self._value is None:
            raise ValueError("Result has no value")
        return self._value

    @property
    def error(self) -> Exception | None:
        """Get the error if any."""
        return self._error

    @classmethod
    def success(cls, value: T) -> Result[T]:
        """Create a successful result."""
        return cls(value=value)

    @classmethod
    def failure(cls, error: Exception) -> Result[T]:
        """Create a failed result."""
        return cls(error=error)


# Async result type
AsyncResult = Awaitable[Result[T]]

# Configuration type with modern syntax
Config = dict[str, JsonValue]

# Event types
Event = dict[str, Any]
EventHandler = AsyncEventHandler
