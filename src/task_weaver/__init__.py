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
)
from .core.program_info import program_manager

from .models.task_models import (
    TaskInfo,
    TaskStatus,
    TaskPriority,
)
from .models.server_models import (
    Server,
    ServerStatus,
    ProgramInfo,
    ResourceType,
)

from .exceptions import (
    ConfigurationError,
    ProcessingError,
)

__version__ = "0.1.0"

# Core functionality
__all__ = [
    # Task Management
    'task_manager',
    'TaskInfo',
    'TaskStatus',
    'TaskPriority',
    'ResourceType',
    
    # Server Management
    'server_manager',
    'Server',
    'ServerStatus',
    
    # Task Registry
    'task_catalog',
    
    # Program Management
    'program_manager',
    'ProgramInfo',
    
    # Exceptions
    'ConfigurationError',
    'ProcessingError',
]

# Usage example:
"""
from task_weaver import (
    task_manager,
    server_manager,
    task_catalog,
    TaskPriority,
    ServerStatus
)

# Register a server
server = server_manager.register_server(
    ip="192.168.1.100",
    name="gpu-1",
    description="GPU Server 1",
    supported_tasks=["image_generation"],
    weight=1
)

# Register a task type
async def process_image(server, task_info, **params):
    # Implementation
    pass

task_catalog.add_task(
    task_name="Image Generation",
    task_type="image_generation",
    executor=process_image
)

# Create and execute a task
task_id = await task_manager.create_task(
    task_type="image_generation",
    params={
        "prompt": "A beautiful sunset",
        "steps": 30
    },
    priority=TaskPriority.HIGH
)

# Get task status
task_info = task_manager.get_task_info(task_id)
"""
