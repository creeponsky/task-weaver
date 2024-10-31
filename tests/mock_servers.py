import asyncio
import random
import threading
import time
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI
from test_utils import logger


class MockServer:
    def __init__(self, port: int, server_type: str):
        self.app = FastAPI()
        self.port = port
        self.server_type = server_type
        
        @self.app.get("/")
        async def health_check():
            logger.info(f"Port {self.port} received health check")
            return {"status": "ok"}
            
        @self.app.post("/execute")
        async def execute_task(task_data: Dict[str, Any]):
            logger.info(f"Port {self.port} received task: {task_data}")
            # Simulate task execution with random delay
            delay = random.uniform(0, 1)
            await asyncio.sleep(delay)
            logger.info(f"Port {self.port} task execution completed: {task_data}")
            return {
                "status": "success",
                "execution_time": delay,
                "server_type": self.server_type,
                "task_data": task_data
            }
    
    def start(self):
        def run_server():
            uvicorn.run(self.app, host="127.0.0.1", port=self.port)
            
        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

# Create server instances
gpu_server_1 = MockServer(8001, "gpu")
gpu_server_2 = MockServer(8002, "gpu")
gpu_server_3 = MockServer(8003, "gpu")

def start_mock_servers():
    gpu_server_1.start()
    gpu_server_2.start()
    gpu_server_3.start()
    # Give servers time to start
    time.sleep(2)