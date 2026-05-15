# Backward-compat shim — canonical source is bobthebot.core.registries
from .core.registries import *  # noqa: F401, F403
from .core.registries import (
    BackendFactory, BackendRegistry, BackendSpec, default_backend_registry,
)
