from typing import Any, Callable, Dict, Optional, List
from ..exceptions import ConfigurationError
from ..models.task_models import TaskDefinition, TaskExecutor
from ..models.server_models import ResourceType
class TaskCatalog:
    """Catalog for managing task definitions and information"""
    
    def __init__(self):
        self._task_catalog: Dict[str, TaskDefinition] = {}
    
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
        if task_type in self._task_catalog:
            return f"Task {task_type} already exists in catalog, you need to change the task_type"
        
        task_def = TaskDefinition(
            showname=task_name,
            task_type=task_type,
            executor=executor,
            required_resource=required_resource,
            description=description,
            version=version
        )
        
        self._task_catalog[task_type] = task_def
    
    def remove_task_definition(self, task_type: str) -> None:
        """Remove a task definition from catalog"""
        if task_type not in self._task_catalog:
            raise ConfigurationError(f"Task {task_type} not found in catalog")
        del self._task_catalog[task_type]
    
    def get_task_definition(self, task_type: str) -> Optional[TaskDefinition]:
        """Get task definition by task type"""
        return self._task_catalog.get(task_type)

# Global task catalog
task_catalog = TaskCatalog()
