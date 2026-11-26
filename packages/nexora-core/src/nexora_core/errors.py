"""Transport-agnostic error hierarchy. Services map these to HTTP/gRPC status codes."""

from __future__ import annotations


class NexoraError(Exception):
    """Base class. `code` is a stable machine-readable identifier."""

    code = "nexora_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(NexoraError):
    code = "not_found"


class ConflictError(NexoraError):
    code = "conflict"


class ValidationFailedError(NexoraError):
    code = "validation_failed"


class UnauthorizedError(NexoraError):
    code = "unauthorized"


class ForbiddenError(NexoraError):
    code = "forbidden"


class AdapterError(NexoraError):
    """An external engine could not be reached or returned an unusable answer."""

    code = "adapter_error"


class ConfigurationError(NexoraError):
    code = "configuration_error"
