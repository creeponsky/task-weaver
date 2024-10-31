from enum import Enum
from typing import Dict, List

from pydantic import BaseModel


# 任务需要的资源类型 | 也是服务器类型 但不严格对等
class ResourceType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    API = "api"

class ServerStatus(str, Enum):
    stop = "stop"
    error = "error"
    idle = "idle"
    occupy = "occupy" #占用状态，这个时候不一定是在跑服务，但是已经被某个任务给捕获了

class TaskTypeStats(BaseModel):
    total: int
    success: int
    failed: int
    avg_duration: float

class ProgramInfo(BaseModel):
    gpu_num: int
    running_gpu_num: int
    #运行时长
    running_time: int
    # 已完成任务数
    finished_task_num: int
    # 失败任务数
    failed_task_num: int
    first_start_time: int
    task_type_stats: Dict[str, TaskTypeStats]


class Server(BaseModel):
    ip: str
    server_name: str
    description: str
    available_task_types: List[str] #服务器可以跑的任务类型
    server_type: ResourceType #服务器资源类型
    status: ServerStatus = ServerStatus.stop
    weight: int = 1

    def check_available_task_type(self, available_task_type: str):
        return available_task_type in self.available_task_types
    #to str
    def __str__(self):
        return f"server_name:{self.server_name}"
    
    def description_str(self):
        return f"Server(ip={self.ip}, server_name={self.server_name}, description={self.description}, status={self.status}, weight={self.weight})"