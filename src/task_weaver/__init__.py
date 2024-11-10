"""
Workflow Manager - A flexible task scheduling and server management library
"""

from .core.program_info import program_manager
from .core.server import (
    server_manager,
)
from .core.task import (
    task_manager,
)
from .core.task_catalog import TaskCompletionCallback, task_catalog
from .exceptions import (
    ConfigurationError,
    ProcessingError,
)
from .log.logger import configure_logging
from .models.server_models import (
    ProgramInfo,
    ResourceType,
    Server,
    ServerStatus,
    ServerTier,
)
from .models.task_models import (
    BaseTaskExecutor,
    Task,
    TaskDefinition,
    TaskInfo,
    TaskPriority,
    TaskStatus,
)


def shutdown():
    """Shutdown the program"""
    program_manager.shutdown()


__version__ = "0.2.1"

# Core functionality
__all__ = [
    # Task Management
    "task_manager",
    "TaskInfo",
    "TaskStatus",
    "TaskPriority",
    "ResourceType",
    "BaseTaskExecutor",
    "Task",
    # Server Management
    "server_manager",
    "Server",
    "ServerStatus",
    "ServerTier",
    # Task Registry
    "task_catalog",
    "TaskDefinition",
    "TaskCompletionCallback",
    # Program Management
    "program_manager",
    "ProgramInfo",
    # Exceptions
    "ConfigurationError",
    "ProcessingError",
    # Logging
    "configure_logging",
    "shutdown",
]
