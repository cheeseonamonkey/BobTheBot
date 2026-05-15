# Backward-compat shim — canonical source is bobthebot.core.tasks
from .core.tasks import *  # noqa: F401, F403
from .core.tasks import (
    IdleTask, InteractTask, MiningTask, Task,
    TaskRegistry, TaskSpec, default_task_registry, validate_task_config,
)
