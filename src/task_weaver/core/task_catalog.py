from typing import Any, Dict, Optional, Callable, List
import asyncio

from ..exceptions import ConfigurationError
from ..models.server_models import ResourceType
from ..models.task_models import TaskDefinition, TaskExecutor, TaskInfo
from ..log.logger import logger

# Type definition for task completion callback
TaskCompletionCallback = Callable[[TaskInfo], asyncio.coroutine]

class TaskCatalog:
    """Catalog for managing task definitions and information"""
    
    def __init__(self):
        self._task_catalog: Dict[str, TaskDefinition] = {}
        self._completion_listeners: Dict[str, List[TaskCompletionCallback]] = {}
    
    def add_task_definition(
        self,
        task_name: str,
        task_type: str,
        executor: TaskExecutor[Any],
        required_resource: ResourceType,
        description: str = "",
        version: str = "1.0.0"
    ) -> None:
        """Add a new task definition to catalog"""
        if not task_name or not task_type:
            raise ConfigurationError("Task name and type cannot be empty")
            
        if not executor:
            raise ConfigurationError("Task executor cannot be None")
            
        if task_type in self._task_catalog:
            raise ConfigurationError(f"Task {task_type} already exists in catalog, you need to change the task_type")
        
        try:
            task_def = TaskDefinition(
                showname=task_name,
                task_type=task_type,
                executor=executor,
                required_resource=required_resource,
                description=description,
                version=version
            )
        except Exception as e:
            logger.error(f"Failed to create task definition: {str(e)}")
            raise ConfigurationError(f"Failed to create task definition: {str(e)}")
        
        self._task_catalog[task_type] = task_def
        self._completion_listeners[task_type] = []
        logger.info(f"Successfully added task definition for {task_type}")
    
    def remove_task_definition(self, task_type: str) -> None:
        """Remove a task definition from catalog"""
        if not task_type:
            raise ConfigurationError("Task type cannot be empty")
            
        if task_type not in self._task_catalog:
            raise ConfigurationError(f"Task {task_type} not found in catalog")
            
        try:
            del self._task_catalog[task_type]
            del self._completion_listeners[task_type]
            logger.info(f"Successfully removed task definition for {task_type}")
        except Exception as e:
            logger.error(f"Failed to remove task definition: {str(e)}")
            raise ConfigurationError(f"Failed to remove task definition: {str(e)}")
    
    def get_task_definition(self, task_type: str) -> Optional[TaskDefinition]:
        """Get task definition by task type"""
        if not task_type:
            raise ConfigurationError("Task type cannot be empty")
        return self._task_catalog.get(task_type)

    def add_completion_listener(self, task_type: str, callback: TaskCompletionCallback) -> None:
        """Add a completion listener for a specific task type"""
        if not task_type:
            raise ConfigurationError("Task type cannot be empty")
            
        if not callback:
            raise ConfigurationError("Callback cannot be None")
            
        if task_type not in self._task_catalog:
            raise ConfigurationError(f"Task type {task_type} not found in catalog")
            
        try:
            if task_type not in self._completion_listeners:
                self._completion_listeners[task_type] = []
            self._completion_listeners[task_type].append(callback)
            logger.debug(f"Added completion listener for task type {task_type}")
        except Exception as e:
            logger.error(f"Failed to add completion listener: {str(e)}")
            raise ConfigurationError(f"Failed to add completion listener: {str(e)}")

    def remove_completion_listener(self, task_type: str, callback: TaskCompletionCallback) -> None:
        """Remove a completion listener for a specific task type"""
        if not task_type or not callback:
            logger.warning("Attempted to remove listener with empty task type or callback")
            return
            
        if task_type not in self._completion_listeners:
            logger.warning(f"No listeners found for task type {task_type}")
            return
            
        try:
            self._completion_listeners[task_type].remove(callback)
            logger.debug(f"Removed completion listener for task type {task_type}")
        except ValueError:
            logger.warning(f"Callback not found for task type {task_type}")
        except Exception as e:
            logger.error(f"Failed to remove completion listener: {str(e)}")
            raise ConfigurationError(f"Failed to remove completion listener: {str(e)}")

    async def notify_task_completion(self, task_info: TaskInfo) -> None:
        """Notify all registered listeners when a task completes"""
        if not task_info:
            raise ConfigurationError("Task info cannot be None")
            
        task_type = task_info.task_type
        if not task_type:
            raise ConfigurationError("Task type cannot be empty")
            
        if task_type in self._completion_listeners:
            for callback in self._completion_listeners[task_type]:
                try:
                    await callback(task_info)
                except Exception as e:
                    logger.error(f"Error in completion callback for task {task_type}: {str(e)}")

# Global task catalog
task_catalog = TaskCatalog()
