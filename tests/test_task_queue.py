import asyncio

import httpx
import pytest
from test_utils import logger

from task_weaver.core.task import task_manager
from task_weaver.core.task_catalog import task_catalog
from task_weaver.exceptions import ConfigurationError
from task_weaver.models.task_models import (
    Any,
    BaseTaskExecutor,
    Dict,
    ResourceType,
    Server,
    Task,
    TaskInfo,
    TaskPriority,
    TaskStatus,
)


# Task executors
class GPUTask1Executor(BaseTaskExecutor[Dict[str, Any]]):
    async def __call__(
        self, server: Server | None, task_info: TaskInfo, **kwargs: Any
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{server.ip}/execute", json=kwargs)
            logger.info(f"GPU Task {task_info.task_id} completed")
            return response.json()


class GPUTask2Executor(BaseTaskExecutor[Dict[str, Any]]):
    async def __call__(
        self, server: Server | None, task_info: TaskInfo, **kwargs: Any
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{server.ip}/execute", json=kwargs)
            logger.info(f"GPU Task {task_info.task_id} completed")
            return response.json()


class APITaskExecutor(BaseTaskExecutor[Dict[str, Any]]):
    async def __call__(
        self, server: Server | None, task_info: TaskInfo, **kwargs: Any
    ) -> Dict[str, Any]:
        # API server is none, just sleep
        await asyncio.sleep(1)
        logger.info(f"API Task {task_info.task_id} completed")
        return {"status": "success"}


@pytest.fixture(autouse=True)
def register_task_types():
    try:
        # Register task types
        task_catalog.add_task_definition(
            "GPU Task 1",
            "gpu_task_1",
            GPUTask1Executor(),
            ResourceType.GPU,
            "Test GPU Task 1",
        )

        task_catalog.add_task_definition(
            "GPU Task 2",
            "gpu_task_2",
            GPUTask2Executor(),
            ResourceType.GPU,
            "Test GPU Task 2",
        )

        task_catalog.add_task_definition(
            "API Task", "api_task", APITaskExecutor(), ResourceType.API, "Test API Task"
        )
    except ConfigurationError as e:
        logger.error(f"Error registering task types: {e}")


@pytest.mark.asyncio
async def test_basic_task_execution():
    """Test basic execution of different task types"""
    logger.info("Starting basic task execution test")

    # Create one task of each type
    tasks = []

    # GPU Task 1
    task1 = await task_manager.create_task(
        task_type="gpu_task_1", priority=TaskPriority.MEDIUM, test_param="gpu1_test"
    )
    await task_manager.add_task(task1)
    tasks.append(task1)
    logger.info(f"Created task {task1.task_info.task_id} (gpu_task_1)")

    # GPU Task 2
    task2 = await task_manager.create_task(
        task_type="gpu_task_2", priority=TaskPriority.MEDIUM, test_param="gpu2_test"
    )
    await task_manager.add_task(task2)
    tasks.append(task2)
    logger.info(f"Created task {task2.task_info.task_id} (gpu_task_2)")

    # API Task
    task3 = await task_manager.create_task(
        task_type="api_task", priority=TaskPriority.MEDIUM, test_param="api_test"
    )
    await task_manager.add_task(task3)
    tasks.append(task3)
    logger.info(f"Created task {task3.task_info.task_id} (api_task)")

    # Wait for tasks to complete using asyncio.gather
    async def wait_for_task(task: Task):
        while True:
            task_info = task_manager.get_task_info(task.task_info.task_id)
            if task_info.status == TaskStatus.FINISH:
                logger.info(
                    f"Task {task.task_info.task_id} ({task.task_info.task_type}) completed successfully"
                )
                return
            await asyncio.sleep(0.5)

    await asyncio.gather(*[wait_for_task(task) for task in tasks])


@pytest.mark.asyncio
async def test_task_priorities():
    """Test task priority execution order"""
    logger.info("Starting task priority test")

    tasks = []
    priorities = [TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]

    # Create GPU tasks with different priorities
    for priority in priorities:
        task = await task_manager.create_task(
            task_type="gpu_task_1",
            priority=priority,
            test_param=f"priority_{priority.value}",
        )
        await task_manager.add_task(task)
        tasks.append(task)
        logger.info(
            f"Created task {task.task_info.task_id} with priority {priority.value}"
        )

    # Wait for tasks to complete using asyncio.gather
    completed_tasks = []

    async def wait_for_priority_task(task: Task):
        while True:
            task_info = task_manager.get_task_info(task.task_info.task_id)
            if task_info.status == TaskStatus.FINISH:
                completed_tasks.append(task)
                logger.info(
                    f"Task {task.task_info.task_id} (Priority: {task_info.priority.value}) completed"
                )
                return
            await asyncio.sleep(0.5)

    await asyncio.gather(*[wait_for_priority_task(task) for task in tasks])
