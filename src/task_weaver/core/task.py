import asyncio
import traceback
import uuid
from datetime import datetime
from typing import Dict, Optional

from ..exceptions import ProcessingError
from ..log.logger import logger
from ..models.server_models import ResourceType, Server
from ..models.task_models import Task, TaskInfo, TaskPriority, TaskStatus
from .program_info import program_manager
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
        logger.info("Initializing TaskManager...")
        # Queue for each task type to enable parallel processing
        self._queues: Dict[str, asyncio.Queue] = {}

        # In-memory storage of active tasks
        self._tasks: Dict[str, Task] = {}

        # Track task processors (coroutines) for each task type
        self._processors: Dict[str, asyncio.Task] = {}

        # Track processor running state
        self._is_processor_running: Dict[str, bool] = {}

        # Lock for processor management
        self._task_lock = asyncio.Lock()
        logger.info("TaskManager initialized successfully")

    async def create_task(
        self, task_type: str, priority: TaskPriority, *args, **kwargs
    ) -> Task:
        """Create a new task instance with the specified parameters."""
        logger.info(f"Creating new task of type {task_type} with priority {priority}")
        try:
            task_definition = task_catalog.get_task_definition(task_type)
            if not task_definition:
                error_msg = f"Task type {task_type} not found in catalog"
                logger.error(error_msg)
                raise ProcessingError(error_msg)

            task_id = str(uuid.uuid4())
            logger.debug(f"Generated task ID: {task_id}")

            task = Task(
                task_info=TaskInfo(
                    task_id=task_id,
                    task_type=task_type,
                    status=TaskStatus.INIT,
                    priority=priority,
                    create_time=datetime.now(),
                    progress=0,
                    remaining_duration=None,
                    wait_duration=None,
                    execution_duration=None,
                    message="Task is queued.",
                ),
                args=args,
                kwargs=kwargs,
            )
            logger.info(f"Successfully created task {task_id} of type {task_type}")
            return task

        except Exception as e:
            error_msg = f"Failed to create task: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise ProcessingError(error_msg)

    # 为什么不直接在create_task中将task置入队列并执行
    # 因为这代表两种不同状态，一个是状态创建INIT、一个是状态预执行，中间或许业务层会有一些自定义操作而不直接入队
    async def add_task(self, task: Task) -> None:
        """Add a task to the processing queue."""
        self._tasks[task.task_info.task_id] = task
        await self._ensure_task_processor(task.task_info.task_type)
        await self._queues[task.task_info.task_type].put(task)
        return task

    async def _ensure_task_processor(self, task_type: str) -> None:
        """Ensure a processor coroutine is running for the given task type."""
        if task_type not in self._queues:
            logger.info(f"Creating new queue for task type {task_type}")
            self._queues[task_type] = asyncio.Queue()
            self._is_processor_running[task_type] = False

        if not self._is_processor_running[task_type]:
            logger.info(f"Starting processor for task type {task_type}")
            async with self._task_lock:
                if not self._is_processor_running[task_type]:
                    self._is_processor_running[task_type] = True
                    self._processors[task_type] = asyncio.create_task(
                        self._process_queue(task_type)
                    )

    async def _process_queue(self, task_type: str) -> None:
        """Process tasks from the queue for a specific task type."""
        logger.info(f"Starting queue processor for task type {task_type}")
        last_warning_time = 0  # Track the last warning time
        warning_interval = 60  # Warning interval in seconds
        try:
            while True:
                task: Task | None = None
                server: Server | None = None
                try:
                    task_definition = task_catalog.get_task_definition(task_type)

                    # Allocate server resources if needed
                    if task_definition.required_resources != ResourceType.API:
                        server = await server_manager.get_idle_server(
                            task_definition.task_type,
                            task_definition.required_resources,
                        )
                        if not server:
                            current_time = datetime.now().timestamp()
                            if current_time - last_warning_time >= warning_interval:
                                logger.warning(
                                    f"No available servers for task type {task_type}, waiting..."
                                )
                                last_warning_time = current_time
                            # Add delay to prevent tight loop
                            await asyncio.sleep(0.5)
                            continue
                        logger.info(
                            f"Allocated server {server.server_name} for task type {task_type}"
                        )

                    task: Task = await self._queues[task_type].get()
                    logger.info(
                        f"Processing task {task.task_info.task_id} of type {task_type}"
                    )
                    await self._execute_task(task, server)
                    await task_catalog.notify_task_completion(task.task_info)

                except asyncio.CancelledError:
                    logger.error(f"Queue processor for {task_type} was cancelled")
                    break
                except Exception as e:
                    error_msg = (
                        f"Error processing task: {str(e)}\n{traceback.format_exc()}"
                    )
                    logger.error(error_msg)
                    if task:
                        task.task_info.status = TaskStatus.FAIL
                        task.task_info.error = error_msg
                finally:
                    if server:
                        logger.debug(f"Releasing server {server.server_name}")
                        await server_manager.release_server(server)
                    if task:
                        logger.debug(
                            f"Marking task {task.task_info.task_id} as done in queue"
                        )
                        self._queues[task_type].task_done()
        except Exception as e:
            logger.error(
                f"Fatal error in _process_queue for {task_type}: {str(e)}\n{traceback.format_exc()}"
            )
        finally:
            logger.warning(f"Queue processor for {task_type} is shutting down")
            self._is_processor_running[task_type] = False

    async def _execute_task(self, task: Task, server: Server | None) -> None:
        """Execute a single task with full lifecycle monitoring."""
        logger.info(f"Starting execution of task {task.task_info.task_id}")
        try:
            task_definition = task_catalog.get_task_definition(task.task_info.task_type)
            if not task_definition or not task_definition.executor:
                error_msg = (
                    f"No executor found for task type: {task.task_info.task_type}"
                )
                logger.error(error_msg)
                raise ProcessingError(error_msg)

            task.task_info.status = TaskStatus.PROCESS
            task.task_info.start_time = datetime.now()
            task.task_info.wait_duration = (
                task.task_info.start_time - task.task_info.create_time
            ).total_seconds()
            logger.info(
                f"Task {task.task_info.task_id} waited {task.task_info.wait_duration:.2f} seconds in queue"
            )

            logger.debug(f"Executing task {task.task_info.task_id} with executor")
            await task_definition.executor(
                server, task.task_info, *task.args, **task.kwargs
            )

            task.task_info.status = TaskStatus.FINISH
            program_manager.update_finished_task_num(task.task_info.task_type)
            task.task_info.message = "Task completed successfully"
            logger.info(f"Task {task.task_info.task_id} completed successfully")

        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            task.task_info.status = TaskStatus.FAIL
            program_manager.update_failed_task_num(task.task_info.task_type)
            task.task_info.error = error_msg
            task.task_info.message = "Task failed"
            raise
        finally:
            task.task_info.finish_time = datetime.now()
            task.task_info.execution_duration = (
                task.task_info.finish_time - task.task_info.start_time
            ).total_seconds()
            logger.info(
                f"Task {task.task_info.task_id} execution took {task.task_info.execution_duration:.2f} seconds"
            )

    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Retrieve task information from memory."""
        # Use class level dict to track task id access counts
        if not hasattr(self, "_task_access_counts"):
            self._task_access_counts = {}
            self._last_log_time = {}
        warning_interval = 10
        current_time = datetime.now().timestamp()

        # Initialize or increment access count
        if task_id not in self._task_access_counts:
            self._task_access_counts[task_id] = 1
            self._last_log_time[task_id] = current_time
        else:
            self._task_access_counts[task_id] += 1

        # Check if 5 seconds have passed since last log
        if current_time - self._last_log_time[task_id] >= warning_interval:
            logger.debug(
                f"Retrieving info for task {task_id} "
                f"(accessed {self._task_access_counts[task_id]} times in last {warning_interval}s)"
            )
            # Reset counter and update last log time
            self._task_access_counts[task_id] = 0
            self._last_log_time[task_id] = current_time

        return self._tasks.get(task_id).task_info


# Global task manager instance for application-wide task management
logger.info("Creating global TaskManager instance")
task_manager = TaskManager()
