from typing import Any, Callable, Dict, Optional, List
from ..exceptions import ConfigurationError
from ..models.task_models import TaskDefinition, TaskResourceType

class TaskCatalog:
    """Catalog for managing task definitions and information"""
    
    def __init__(self):
        self._task_catalog: Dict[str, TaskDefinition] = {}
    
    def add_task(
        self,
        task_name: str,
        task_type: str,
        executor: Callable[..., Any],
        required_resource: TaskResourceType,
        description: str = "",
        version: str = "1.0.0"
    ) -> None:
        """Add a new task definition to catalog"""
        if task_type in self._task_catalog:
            raise ConfigurationError(f"Task {task_type} already exists in catalog")
        
        task_def = TaskDefinition(
            name=task_name,
            task_type=task_type,
            executor=executor,
            required_resource=required_resource,
            description=description,
            version=version
        )
        
        self._task_catalog[task_type] = task_def
    
    def remove_task(self, task_type: str) -> None:
        """Remove a task definition from catalog"""
        if task_type not in self._task_catalog:
            raise ConfigurationError(f"Task {task_type} not found in catalog")
        del self._task_catalog[task_type]
    
    def get_task_info(self, task_type: str) -> Optional[TaskDefinition]:
        """Get task definition by task type"""
        return self._task_catalog.get(task_type)

# Global task catalog
task_catalog = TaskCatalog()
