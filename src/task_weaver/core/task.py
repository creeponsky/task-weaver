import asyncio
import json
import traceback
import uuid
from datetime import datetime
from typing import Dict, Optional

from ..exceptions import ProcessingError
from ..models.server_models import ResourceType, Server
from ..models.task_models import TaskInfo, TaskPriority, TaskStatus
from ..utils.cache import CacheManager, CacheType
from .server import server_manager
from .task_catalog import task_catalog


class TaskManager:
    """Core task management functionality for distributed task processing.
    
    This class handles:
    - Task creation and queuing
    - Task execution and monitoring
    - Task status persistence and retrieval
    - Server resource allocation
    - Error handling and recovery
    
    The TaskManager maintains separate queues for different task types and ensures
    tasks are processed according to their priorities while managing server resources.
    """
    
    def __init__(self):
        # Queue for each task type to enable parallel processing
        self._queues: Dict[str, asyncio.Queue] = {}
        
        # Cache manager for task persistence
        self._cache_manager = CacheManager("task_cache", CacheType.TASK)
        
        # In-memory storage of active tasks
        self._tasks: Dict[str, TaskInfo] = {}
        
        # Track task processors (coroutines) for each task type
        self._processors: Dict[str, asyncio.Task] = {}
        
        # Track processor running state
        self._is_processor_running: Dict[str, bool] = {}
        
        # Lock for processor management
        self._task_lock = asyncio.Lock()
    
    async def create_task(
        self,
        task_type: str,
        priority: TaskPriority,
        *args, **kwargs
    ) -> TaskInfo:
        """Create a new task instance with the specified parameters.
        
        Args:
            task_type: The type of task to create (must be registered in task_catalog)
            priority: Task priority level (BEST/HIGH/MEDIUM/LOW)
            *args: Positional arguments to pass to the task executor
            **kwargs: Keyword arguments to pass to the task executor
            
        Returns:
            TaskInfo: The created task instance with initialized tracking fields
            
        Raises:
            ProcessingError: If task type is not found or creation fails
        """
        try:
            task_definition = task_catalog.get_task_definition(task_type)
            if not task_definition:
                raise ProcessingError(f"Task type {task_type} not found in catalog")

            task_id = str(uuid.uuid4())
            task = TaskInfo(
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.INIT,
                priority=priority,
                args=args,
                kwargs=kwargs,
                create_time=datetime.now(),
                progress=0,
                remaining_duration=None,
                wait_duration=None,
                execution_duration=None,
                message="Task is queued."
            )
            return task

        except Exception as e:
            error_msg = f"Failed to create task: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise ProcessingError(error_msg)
        
    async def add_task(self, task: TaskInfo) -> None:
        """Add a task to the processing queue.
        
        This method:
        1. Stores the task in memory
        2. Ensures a processor exists for the task type
        3. Adds task to the processing queue
        4. Persists task to cache
        
        Args:
            task: The TaskInfo instance to queue for processing
            
        Returns:
            The added task instance
        """
        self._tasks[task.task_id] = task
        await self._ensure_task_processor(task.task_type)
        await self._queues[task.task_type].put(task)
        self._save_task_to_cache(task)
        return task

    def _save_task_to_cache(self, task: TaskInfo) -> None:
        """Persist task information to cache storage.
        
        Serializes and stores the full task state for recovery and status tracking.
        Failures are logged but don't interrupt task processing.
        """
        try:
            self._cache_manager.write_cache([{
                'task_id': task.task_id,
                'data': json.dumps(task.model_dump())
            }])
        except Exception as e:
            print(f"Failed to save task to cache: {str(e)}")

    async def _ensure_task_processor(self, task_type: str) -> None:
        """Ensure a processor coroutine is running for the given task type.
        
        Creates a new processor if one doesn't exist. Uses locking to prevent
        duplicate processor creation. Each task type has its own dedicated processor.
        """
        if task_type not in self._queues:
            self._queues[task_type] = asyncio.Queue()
            self._is_processor_running[task_type] = False

        if not self._is_processor_running[task_type]:
            async with self._task_lock:
                if not self._is_processor_running[task_type]:
                    self._is_processor_running[task_type] = True
                    self._processors[task_type] = asyncio.create_task(
                        self._process_queue(task_type)
                    )

    async def _process_queue(self, task_type: str) -> None:
        """Process tasks from the queue for a specific task type.
        
        Handles:
        - Server resource allocation
        - Task execution
        - Error handling and recovery
        - Resource cleanup
        
        Runs continuously until cancelled, processing tasks sequentially
        while managing server resources and handling failures gracefully.
        """
        try:
            while True:
                task = None
                server = None
                try:
                    task_definition = task_catalog.get_task_definition(task_type)
                    
                    # Allocate server resources if needed
                    if task_definition.required_resources != ResourceType.API:
                        server = await server_manager.get_idle_server(
                            task_definition.task_type,
                            task_definition.required_resources
                        )
                        if not server:
                            continue

                    task: TaskInfo = await self._queues[task_type].get()
                    await self._execute_task(task, server)

                except asyncio.CancelledError:
                    print(f"Queue processor for {task_type} was cancelled")
                    break
                except Exception as e:
                    error_msg = f"Error processing task: {str(e)}\n{traceback.format_exc()}"
                    print(error_msg)
                    if task:
                        task.status = TaskStatus.FAIL
                        task.error = error_msg
                        self._save_task_to_cache(task)
                finally:
                    if server:
                        server_manager.release_server(server)
                    if task:
                        self._queues[task_type].task_done()
        finally:
            self._is_processor_running[task_type] = False

    async def _execute_task(self, task: TaskInfo, server: Server | None) -> None:
        """Execute a single task with full lifecycle monitoring.
        
        Handles:
        - Task status updates
        - Timing and duration tracking
        - Result capture
        - Error handling
        - State persistence
        
        Args:
            task: The task to execute
            server: Optional server instance for resource-dependent tasks
        """
        try:
            task_definition = task_catalog.get_task_definition(task.task_type)
            if not task_definition or not task_definition.executor:
                raise ProcessingError(f"No executor found for task type: {task.task_type}")
            
            task.status = TaskStatus.PROCESS
            task.start_time = datetime.now()
            task.wait_duration = (task.start_time - task.create_time).total_seconds()
            self._save_task_to_cache(task)
            
            result = await task_definition.executor(
                server=server,
                task_info=task,
                *task.args,
                **task.kwargs
            )
            
            task.result = result
            task.status = TaskStatus.FINISH
            task.message = "Task completed successfully"
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            task.status = TaskStatus.FAIL
            task.error = error_msg
            task.message = "Task failed"
            raise
        finally:
            task.finish_time = datetime.now()
            task.execution_duration = (task.finish_time - task.start_time).total_seconds()
            self._save_task_to_cache(task)

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Retrieve task information from memory or cache.
        
        First checks in-memory storage, then falls back to cache storage.
        
        Args:
            task_id: The unique identifier of the task
            
        Returns:
            TaskInfo if found, None otherwise
            
        Note:
            Cache retrieval failures are logged but won't raise exceptions
        """
        task = self._tasks.get(task_id)
        if not task:
            try:
                cached_tasks = self._cache_manager.read_cache()
                for cached_task in cached_tasks:
                    if cached_task.get('task_id') == task_id:
                        task_data = json.loads(cached_task['data'])
                        return TaskInfo.from_json(task_data)
            except Exception as e:
                print(f"Failed to get task from cache: {str(e)}")
                print(f"Task {task_id} not found")
        return task

# Global task manager instance for application-wide task management
task_manager = TaskManager()
