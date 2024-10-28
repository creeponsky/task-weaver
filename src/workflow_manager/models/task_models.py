from pydantic import BaseModel
from enum import Enum
from typing import List, Dict, Union, Any, Optional, Callable
from datetime import datetime
from typing import Dict

class TaskStatus(str, Enum):
    INIT = "INIT"
    PROCESS = "PROCESS"
    FINISH = "FINISH"
    FAIL = "FAIL"

class TaskPriority(str, Enum):
    BEST = "BEST"
    HIGH = "HIGH" 
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @property
    def priority(self) -> int:
        priorities = {
            self.BEST: 4,
            self.HIGH: 3,
            self.MEDIUM: 2,
            self.LOW: 1
        }
        return priorities[self]

    def __lt__(self, other):
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.priority < other.priority

    def __gt__(self, other):
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.priority > other.priority

    def __le__(self, other):
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.priority <= other.priority

    def __ge__(self, other):
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.priority >= other.priority

class TaskResourceType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    API = "api"

class TaskDefinition:
    """Definition of a task type that plugins can register"""
    def __init__(
        self,
        name: str,
        task_type: str,
        executor: Callable,
        required_resources: List[TaskResourceType],
        description: str = "",
        version: str = "1.0.0"
    ):
        self.name = name
        self.task_type = task_type
        self.executor = executor
        self.required_resources = required_resources
        self.description = description
        self.version = version

class TaskInfo(BaseModel):
    """Information about a specific task instance"""
    task_id: str
    type: str  # References TaskDefinition.task_type
    status: TaskStatus
    priority: TaskPriority = TaskPriority.MEDIUM
    params: Dict[str, Any]
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress: float = 0
    remaining_time: Optional[float] = None
    wait_time: Optional[float] = None
    execute_time: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    msg: str = "Task is queued."
    
    def model_dump(self):
        return {
            "task_id": self.task_id,
            "type": self.type,
            "status": self.status,
            "priority": self.priority,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "message": self.msg,
            "result": self.result,
            "error": self.error
        }


class TaskQueueItem:
    """Class representing an item in the task queue"""
    def __init__(self, priority: int, task: TaskInfo):
        self.priority = priority
        self.task = task
        
    def __lt__(self, other):
        if not isinstance(other, TaskQueueItem):
            return NotImplemented
        return self.priority < other.priority

