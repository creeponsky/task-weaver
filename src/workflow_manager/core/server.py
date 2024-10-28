from typing import List, Dict, Optional, Any
import asyncio
import httpx
from ..exceptions import ProcessingError, ConfigurationError
from ..utils.cache import CacheManager
from typing import Union, List, Optional
from ..models.server_models import *
from ..core.program_info import program_manager
import asyncio
from typing import List, Dict, Union, Any
import httpx

# TODO 这里还需要每个插件当添加server的时候因为server是由可运行的任务类型的，对应的任务类型的插件就执行runningserver的连接测试，来确保服务可用

class ServerManager:
    def __init__(self):
        self.cache_manager = CacheManager("Cache/server_cache.db")
        self.all_servers = self._load_servers()
        self.server_idle_event: Dict[str, asyncio.Event] = {}
        self.running_servers: List[Server] = []
        asyncio.run(self._init_running_server())
        #maybe try to load the running all_servers from the cache file?

    def _ensure_server_idle_event(self, server_type: str):
        """Ensure server_idle_event has an Event for the given server type"""
        if server_type not in self.server_idle_event:
            self.server_idle_event[server_type] = asyncio.Event()
            self.server_idle_event[server_type].set()

    #还得考虑启动服务的纠正问题，目前想法是启动的时候向服务器发一个请求看服务是否正常返回
    async def _init_running_server(self):
        self.running_servers: List[Server] = []
        running_num = 0
        for server in self.all_servers:
            if server.status == ServerStatus.error or server.status == ServerStatus.occupy:
            # 尝试连接，如果成功则设置为idle，否则设置为stop
                is_connected = await self.check_server(server)
                if is_connected:
                    print(f"服务器${server} error,但是重连成功")
                    self.set_server_status(server, ServerStatus.idle)
                else:
                    print(f"服务器${server} error,重连失败")
                    self.set_server_status(server, ServerStatus.stop)
            if server.status != ServerStatus.stop:
                self.running_servers.append(server)
                running_num += 1
                if server.status != ServerStatus.idle:
                    self.set_server_status(server, ServerStatus.idle)
        
        program_manager.set_running_gpu_num(running_num)
        program_manager.set_gpu_num(len(self.all_servers))

    def _load_servers(self) -> List[Server]:
        """从缓存加载服务器列表"""
        data = self.cache_manager.read_cache()
        return [Server(**server_data) for server_data in data]

    def _save_servers(self):
        """保存服务器列表到缓存"""
        data = [server.model_dump() for server in self.all_servers]
        self.cache_manager.write_cache(data)

    def get_server_by_identifier(self, ip: Union[str, None] = None, server_name: Union[str, None] = None) -> Optional[Server]:
        for server in self.all_servers:
            if ip and server.ip == ip:
                return server
            if server_name and server.server_name == server_name:
                return server
        return None
    
    def check_has_idle(self, server_type: str = None):
        for server in self.running_servers:
            if server.status == ServerStatus.idle and (not server_type or server.check_available_task_type(server_type)):
                return True
        if server_type is None:
            for server_type in self.server_idle_event:
                self._ensure_server_idle_event(server_type)
                self.server_idle_event[server_type].clear()
        else:
            self._ensure_server_idle_event(server_type)
            self.server_idle_event[server_type].clear()
        return False
    
    #检查是否在running_servers中
    def check_server_running(self, server: Server):
        return server in self.running_servers

    #注册服务器，让其处于运行状态
    def register_server(self, ip: str, server_name: str, description, weight, server_types: List[str] = None):
        old_server = self.get_server_by_identifier(ip, server_name)
        if old_server:
            print(f"已经存在服务器：{old_server}")
            #复写
            old_server.ip = ip
            old_server.server_name = server_name
            old_server.description = description
            old_server.weight = weight
            old_server.available_task_types = server_types if server_types else []
            message = f"存在服务器：{old_server}， 已经覆盖配置"
            print(message)
        else:
            server = Server(ip=ip, server_name=server_name, description=description, weight=weight, available_task_types=server_types if server_types else [])
            self.all_servers.append(server)
            message = f"添加新服务器：{server}"
            print(message)

        self._save_servers()
        program_manager.set_gpu_num(len(self.all_servers))
        return True, message

    def add_running_server(self, ip: Union[str, None] = None, server_name: Union[str, None] = None):
        server = self.get_server_by_identifier(ip, server_name)
        if not server:
            print(f"ip:{ip} server_name:{server_name} 服务器不存在")
            return False, f"ip:{ip} server_name:{server_name} 服务器不存在"
        is_running = self.check_server_running(server)
        if is_running:
            print(f"服务器{server}已经在运行")
            return False, f"服务器{server}已经在运行"
        self.running_servers.append(server)
        self.set_server_status(server, ServerStatus.idle)

        program_manager.set_running_gpu_num(len(self.running_servers))
        return True, f"添加服务器{server} 成功"

    def remove_running_server(self, ip: Union[str, None] = None, server_name: Union[str, None] = None):
        server = self.get_server_by_identifier(ip, server_name)
        if not server:
            return False, f"ip:{ip} server_name:{server_name} 服务器不存在"
        is_running = self.check_server_running(server)
        if not is_running:
            return False, f"服务器{server}不在运行"
        if server.status != ServerStatus.idle:
            return False, f"服务器{server}有任务在执行，不在空闲状态，请稍后再关闭"
        self.set_server_status(server, ServerStatus.stop)
        self.running_servers.remove(server)
        program_manager.set_running_gpu_num(len(self.running_servers))
        return True, f"删除服务器{server} 成功"

    async def get_idle_server(self, available_task_type: str = None, task_resource_type: TaskResourceType = None) -> Optional[Server]:
        best_server = None
        while best_server is None:
            for server in self.running_servers:
                if server.status == ServerStatus.error:
                    is_connected = await self.check_server(server)
                    if is_connected:
                        self.set_server_status(server, ServerStatus.idle)
                    else:
                        self.set_server_status(server, ServerStatus.stop)
                        continue
                if server.status == ServerStatus.idle and (not available_task_type or server.check_available_task_type(available_task_type)) and (not task_resource_type or server.server_type == task_resource_type):
                    if best_server is None or best_server.weight < server.weight:
                        best_server = server
            if not best_server:
                if available_task_type:
                    self._ensure_server_idle_event(available_task_type)
                    self.server_idle_event[available_task_type].clear()
                return None
            #发起一次通信，检查服务器是否正常
            is_connected = await self.check_server(best_server)
            if not is_connected:
                self.set_server_status(best_server, ServerStatus.error)
                print(f"运行服务器({best_server})异常，无法连接")
                best_server = None
        self.set_server_status(best_server, ServerStatus.occupy)
        return best_server
    

    async def check_server(self, server: Server):
        for i in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{server.ip}", timeout=20)
                    if response.status_code == 200:
                        return True
                    else:
                        print(f"check_server: 服务器({server})返回异常状态码：{response}")
                        return False
            except httpx.ConnectError:
                if i < 2:  # 如果不是最后一次尝试，那么等待20秒后重试
                    await asyncio.sleep(5)  # 使用 asyncio.sleep 替代 time.sleep
                else:  # 如果是最后一次尝试，那么返回False
                    return False
            except Exception as e:
                print(f"check_server: 服务器({server})异常：{e}")
                return False
        return True
    
    #归还服务器
    def release_server(self, server: Server):
        if server not in self.running_servers:
            return False
        if server.status == ServerStatus.error:
            return False
        self.set_server_status(server, ServerStatus.idle)
        return True
    
    def set_server_status(self, server: Server, status: ServerStatus):
        # if server not in self.running_servers:
        #     return False
        server.status = status
        
        if status == ServerStatus.idle:
            for server_type in server.available_task_types:
                self._ensure_server_idle_event(server_type)
                self.server_idle_event[server_type].set()

        self._save_servers()
        return True
        

server_manager = ServerManager()
