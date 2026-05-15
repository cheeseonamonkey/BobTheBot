# Backward-compat shim — canonical source is bobthebot.core.registries
from .core.registries import (  # noqa: F401
    BackendFactory, BackendRegistry, BackendSpec, default_backend_registry,
)

__all__ = ["BackendFactory", "BackendRegistry", "BackendSpec", "default_backend_registry"]
