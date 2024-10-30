import pytest
import asyncio
from pathlib import Path
from task_weaver.core.server import server_manager
from task_weaver.core.task_catalog import task_catalog
from task_weaver.models.server_models import ResourceType
from test_utils import logger
import logging

# 获取当前文件所在目录的路径
current_dir = Path(__file__).parent
# 导入同目录下的 mock_servers.py
from mock_servers import start_mock_servers

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_test_environment():
    logger.info("Setting up test environment...")
    # Start mock servers
    start_mock_servers()
    
    # Register servers
    server_manager.register_server(
        ip="http://127.0.0.1:8001",
        server_name="gpu_server_1",
        description="GPU Test Server 1",
        weight=1,
        available_task_types=["gpu_task_1", "gpu_task_2"],
        server_type=ResourceType.GPU
    )
    
    server_manager.register_server(
        ip="http://127.0.0.1:8002",
        server_name="gpu_server_2",
        description="GPU Test Server 2",
        weight=1,
        available_task_types=["gpu_task_1", "gpu_task_2"],
        server_type=ResourceType.GPU
    )
    
    server_manager.register_server(
        ip="http://127.0.0.1:8003",
        server_name="gpu_server_3",
        description="GPU Test Server 3",
        weight=1,
        available_task_types=["gpu_task_1", "gpu_task_2"],
        server_type=ResourceType.GPU
    )
    
    # Add servers to running pool
    server_manager.add_running_server(server_name="gpu_server_1")
    server_manager.add_running_server(server_name="gpu_server_2")
    server_manager.add_running_server(server_name="gpu_server_3") 