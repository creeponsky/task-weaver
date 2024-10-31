import asyncio
from pathlib import Path

import pytest
from test_utils import logger

from task_weaver.core.server import server_manager
from task_weaver.models.server_models import ResourceType, ServerTier

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
        tier=ServerTier.STANDARD,
        available_task_types=["gpu_task_1", "gpu_task_2"],
        server_type=ResourceType.GPU
    )
    
    server_manager.register_server(
        ip="http://127.0.0.1:8002",
        server_name="gpu_server_2",
        description="GPU Test Server 2",
        tier=ServerTier.STANDARD,
        available_task_types=["gpu_task_1", "gpu_task_2"],
        server_type=ResourceType.GPU
    )
    
    server_manager.register_server(
        ip="http://127.0.0.1:8003",
        server_name="gpu_server_3",
        description="GPU Test Server 3",
        tier=ServerTier.MINIMAL,
        available_task_types=["gpu_task_1", "gpu_task_2"],
        server_type=ResourceType.GPU
    )
    
    # Add servers to running pool
    await server_manager.add_running_server(server_name="gpu_server_1")
    await server_manager.add_running_server(server_name="gpu_server_2")
    await server_manager.add_running_server(server_name="gpu_server_3") 