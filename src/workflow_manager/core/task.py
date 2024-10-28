from datetime import datetime, timedelta
from typing import Optional, Any, Dict, Tuple, Callable
import asyncio
import uuid
from .server import server_manager
from ..models.task_models import *
from .task_catalog import task_catalog
from ..exceptions import ProcessingError
import traceback

class TaskManager:
    """Task management functionality"""
    
    def __init__(self):
        # Separate queues for different task types
        self._queues: Dict[str, asyncio.Queue] = {}
        self._tasks: Dict[str, TaskInfo] = {}
        self._processors: Dict[str, asyncio.Task] = {}
        self._is_processor_running: Dict[str, bool] = {}
        self._task_lock = asyncio.Lock()
    
    async def create_task(
        self,
        task_type: str,
        params: Dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """Create a new task with enhanced tracking"""
        try:
            task_definition = task_catalog.get_task_info(task_type)
            if not task_definition:
                raise ProcessingError(f"Task type {task_type} not found in catalog")

            task_id = str(uuid.uuid4())
            task = TaskInfo(
                task_id=task_id,
                type=task_type,
                status=TaskStatus.INIT,
                priority=priority,
                params=params,
                created_at=datetime.now(),
                progress=0,
                remaining_time=None,
                wait_time=None,
                execute_time=None,
                msg="Task is queued."
            )
            
            async with self._task_lock:
                self._tasks[task_id] = task
                await self._ensure_task_processor(task_type)
                await self._queues[task_type].put(task)
            
            return task_id

        except Exception as e:
            error_msg = f"Failed to create task: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            raise ProcessingError(error_msg)

    async def _ensure_task_processor(self, task_type: str) -> None:
        """Ensure task processor is running for the task type"""
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
        """Enhanced queue processor with better error handling"""
        try:
            while True:
                task = None
                server = None
                try:
                    task: TaskInfo = await self._queues[task_type].get()
                    task_definition = task_catalog.get_task_info(task.type)
                    
                    # Server allocation logic
                    if task_definition.required_resources != TaskResourceType.API:
                        wait_start = datetime.now()
                        server = await server_manager.get_idle_server(
                            task_definition.task_type,
                            task_definition.required_resources
                        )
                        if not server:
                            # Put task back in queue if no server available
                            await self._queues[task_type].put(task)
                            continue
                        task.wait_time = (datetime.now() - wait_start).total_seconds()

                    # Execute task
                    start_time = datetime.now()
                    await self._execute_task(task, server)
                    task.execute_time = (datetime.now() - start_time).total_seconds()

                except asyncio.CancelledError:
                    print(f"Queue processor for {task_type} was cancelled")
                    break
                except Exception as e:
                    error_msg = f"Error processing task: {str(e)}\n{traceback.format_exc()}"
                    print(error_msg)
                    if task:
                        task.status = TaskStatus.FAIL
                        task.error = error_msg
                finally:
                    if server:
                        server_manager.release_server(server)
                    if task:
                        self._queues[task_type].task_done()
        finally:
            self._is_processor_running[task_type] = False

    async def _execute_task(self, task: TaskInfo, server: Optional[Any]) -> None:
        """Execute task with enhanced monitoring"""
        try:
            task_definition = task_catalog.get_task_info(task.type)
            if not task_definition or not task_definition.executor:
                raise ProcessingError(f"No executor found for task type: {task.type}")
            
            task.status = TaskStatus.PROCESS
            task.started_at = datetime.now()
            
            result = await task_definition.executor(
                server=server,
                task_info=task,
                **task.params
            )
            
            task.result = result
            task.status = TaskStatus.FINISH
            task.msg = "Task completed successfully"
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            task.status = TaskStatus.FAIL
            task.error = error_msg
            task.msg = "Task failed"
            raise
        finally:
            task.finished_at = datetime.now()

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information"""
        task = self._tasks.get(task_id)
        if not task:
            print(f"Task {task_id} not found")
        return task

# Global task manager instance
task_manager = TaskManager()
