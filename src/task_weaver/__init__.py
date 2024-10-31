"""
Workflow Manager - A flexible task scheduling and server management library
"""

from .core.task import (
    task_manager,
)
from .core.server import (
    server_manager,
)
from .core.task_catalog import (
    task_catalog,
    TaskCompletionCallback
)
from .core.program_info import program_manager

from .models.task_models import (
    TaskInfo,
    TaskStatus,
    BaseTaskExecutor,
    TaskPriority,
)
from .models.server_models import (
    Server,
    ServerStatus,
    ProgramInfo,
    ServerTier,
    ResourceType,
)

from .exceptions import (
    ConfigurationError,
    ProcessingError,
)
from .log.logger import configure_logging
__version__ = "0.1.0"

# Core functionality
__all__ = [
    # Task Management
    'task_manager',
    'TaskInfo',
    'TaskStatus',
    'TaskPriority',
    'ResourceType',
    'BaseTaskExecutor',
    # Server Management
    'server_manager',
    'Server',
    'ServerStatus',
    'ServerTier',
    # Task Registry
    'task_catalog',
    'TaskCompletionCallback',
    # Program Management
    'program_manager',
    'ProgramInfo',
    
    # Exceptions
    'ConfigurationError',
    'ProcessingError',

    # Logging
    'configure_logging',
]