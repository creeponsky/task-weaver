from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Protocol, TypeVar

from pydantic import BaseModel

from .server_models import ResourceType, Server

T = TypeVar('T')  # Return type for executor

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


class TaskInfo(BaseModel):
    """Information about a specific task instance"""
    task_id: str
    task_type: str  # References TaskDefinition.task_type
    status: TaskStatus
    priority: TaskPriority = TaskPriority.MEDIUM
    args: Any = None
    kwargs: Any = None
    create_time: datetime = datetime.now()
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None
    progress: float = 0 # 0-100的百分比
    remaining_duration: Optional[float] = None # 剩余时间
    wait_duration: Optional[float] = None # 等待时间
    execution_duration: Optional[float] = None # 执行时间
    result: Optional[Any] = None
    error: Optional[str] = None
    message: str = "Task is queued."
    
    def model_dump(self) -> Dict[str, Any]:
        """Serialize the model with datetime handling"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "priority": self.priority,
            "progress": self.progress,
            "params": self.params,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "finish_time": self.finish_time.isoformat() if self.finish_time else None,
            "message": self.message,
            "remaining_duration": self.remaining_duration,
            "wait_duration": self.wait_duration,
            "execution_duration": self.execution_duration,
            "result": self.result,
            "error": self.error
        }
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "TaskInfo":
        """Create TaskInfo instance from JSON data with datetime handling"""
        # Convert ISO format strings to datetime objects
        if isinstance(data.get('create_time'), str):
            data['create_time'] = datetime.fromisoformat(data['create_time'])
        if isinstance(data.get('start_time'), str):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if isinstance(data.get('finish_time'), str):
            data['finish_time'] = datetime.fromisoformat(data['finish_time'])
        return cls(**data)


class TaskExecutor(Protocol[T]):
    """Type protocol for task executors"""
    async def __call__(
        self,
        server: Server | None,
        task_info: TaskInfo,
        **kwargs: Any
    ) -> T: ...

class TaskDefinition:
    """Definition of a task type that plugins can register"""
    def __init__(
        self,
        showname: str,
        task_type: str,
        executor: TaskExecutor[Any],
        required_resource: ResourceType,
        description: str = "",
        version: str = "1.0.0"
    ):
        self.name = showname
        self.task_type = task_type
        self.executor = executor
        self.required_resources = required_resource
        self.description = description
        self.version = version

class TaskQueueItem:
    """Class representing an item in the task queue"""
    def __init__(self, priority: int, task: TaskInfo):
        self.priority = priority
        self.task = task
        
    def __lt__(self, other):
        if not isinstance(other, TaskQueueItem):
            return NotImplemented
        return self.priority < other.priority

