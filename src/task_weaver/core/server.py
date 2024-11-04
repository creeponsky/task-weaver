import asyncio
import time
from typing import Dict, List, Optional, Union

import httpx

from ..core.program_info import program_manager
from ..log.logger import logger
from ..models.server_models import ResourceType, Server, ServerStatus, ServerTier
from ..utils.cache import CacheManager, CacheType

# TODO 这里还需要每个插件当添加server的时候因为server是由可运行的任务类型的，对应的任务类型的插件就执行runningserver的连接测试，来确保服务可用


class ServerManager:
    def __init__(self):
        self.cache_manager = CacheManager("server_cache", CacheType.SERVER)
        self.all_servers = self._load_servers()
        self.server_idle_event: Dict[str, asyncio.Event] = {}
        self.running_servers: List[Server] = []
        self.initialized = False
        self._lock = asyncio.Lock()

        # Optimized data structures
        self.servers_by_status: Dict[ServerStatus, List[Server]] = {
            status: [] for status in ServerStatus
        }
        self.servers_by_type: Dict[str, List[Server]] = {}

    async def ensure_initialized(self):
        """Ensure the manager is initialized before use"""
        if not self.initialized:
            await self._init_running_server()
            self.initialized = True

    def _ensure_server_idle_event(self, server_type: str):
        """Ensure server_idle_event has an Event for the given server type"""
        if server_type not in self.server_idle_event:
            self.server_idle_event[server_type] = asyncio.Event()
            self.server_idle_event[server_type].set()

    async def _init_running_server(self):
        start_time = time.time()
        self.running_servers: List[Server] = []
        running_num = 0
        for server in self.all_servers:
            if (
                server.status == ServerStatus.error
                or server.status == ServerStatus.occupy
            ):
                # 尝试连接，如果成功则设置为idle，否则设置为stop
                is_connected = await self.check_server(server)
                if is_connected:
                    logger.info(f"服务器{server} error,但是重连成功")
                    self.set_server_status(server, ServerStatus.idle)
                else:
                    logger.info(f"服务器{server} error,重连失败")
                    self.set_server_status(server, ServerStatus.stop)
            if server.status != ServerStatus.stop:
                self.running_servers.append(server)
                running_num += 1
                if server.status != ServerStatus.idle:
                    self.set_server_status(server, ServerStatus.idle)

        program_manager.set_running_gpu_num(running_num)
        program_manager.set_gpu_num(len(self.all_servers))

        # Initialize optimized data structures
        self._update_server_indices()
        await program_manager.record_operation_time("init_running_server", start_time)

    def _update_server_indices(self):
        """Update the optimized server indices"""
        # Clear existing indices
        for status in ServerStatus:
            self.servers_by_status[status] = []
        self.servers_by_type.clear()

        # Rebuild indices
        for server in self.all_servers:
            self.servers_by_status[server.status].append(server)
            for task_type in server.available_task_types:
                if task_type not in self.servers_by_type:
                    self.servers_by_type[task_type] = []
                self.servers_by_type[task_type].append(server)

    def _load_servers(self) -> List[Server]:
        """从缓存加载服务器列表"""
        data = self.cache_manager.read_cache()
        return [Server(**server_data) for server_data in data]

    def _save_servers(self):
        """保存服务器列表到缓存"""
        data = [server.model_dump() for server in self.all_servers]
        self.cache_manager.write_cache(data)
        self._update_server_indices()

    def get_server_by_identifier(
        self, ip: Union[str, None] = None, server_name: Union[str, None] = None
    ) -> Optional[Server]:
        for server in self.all_servers:
            if ip and server.ip == ip:
                return server
            if server_name and server.server_name == server_name:
                return server
        return None

    def check_has_idle(self, server_type: str = None):
        idle_servers = self.servers_by_status[ServerStatus.idle]
        if server_type:
            return any(
                server
                for server in idle_servers
                if server.check_available_task_type(server_type)
            )
        return bool(idle_servers)

    def check_server_running(self, server: Server):
        return server in self.running_servers

    async def register_server(
        self,
        ip: str,
        server_name: str,
        description,
        tier: ServerTier,
        available_task_types: List[str] = None,
        server_type: ResourceType = ResourceType.GPU,
    ):
        start_time = time.time()
        async with self._lock:
            old_server = self.get_server_by_identifier(ip, server_name)
            if old_server:
                logger.info(f"已经存在服务器：{old_server}")
                old_server.ip = ip
                old_server.server_name = server_name
                old_server.description = description
                old_server.tier = tier
                old_server.available_task_types = (
                    available_task_types if available_task_types else []
                )
                old_server.server_type = (
                    server_type if server_type else old_server.server_type
                )
                message = f"存在服务器：{old_server}， 已经覆盖配置"
                logger.info(message)
            else:
                server = Server(
                    ip=ip,
                    server_name=server_name,
                    description=description,
                    tier=tier,
                    available_task_types=available_task_types
                    if available_task_types
                    else [],
                    server_type=server_type,
                )
                self.all_servers.append(server)
                message = f"添加新服务器：{server}"
                logger.info(message)

            self._save_servers()
            program_manager.set_gpu_num(len(self.all_servers))
            await program_manager.record_operation_time("register_server", start_time)
            return True, message

    async def get_idle_server(
        self, available_task_type: str = None, task_resource_type: ResourceType = None
    ) -> Optional[Server]:
        start_time = time.time()
        await self.ensure_initialized()
        async with self._lock:
            idle_servers = self.servers_by_status[ServerStatus.idle]

            if available_task_type:
                type_servers = self.servers_by_type.get(available_task_type, [])
                idle_servers = [
                    s
                    for s in idle_servers
                    if s.check_available_task_type(available_task_type)
                ]

            if task_resource_type:
                idle_servers = [
                    s for s in idle_servers if s.server_type == task_resource_type
                ]

            idle_servers.sort(key=lambda x: x.tier.value, reverse=True)

            for server in idle_servers:
                if await self.check_server(server):
                    self.set_server_status(server, ServerStatus.occupy)
                    if available_task_type:
                        await program_manager.record_task_time(
                            available_task_type, start_time
                        )
                    return server
                self.set_server_status(server, ServerStatus.error)
                logger.error(f"运行服务器({server})异常，无法连接")

            if available_task_type:
                self._ensure_server_idle_event(available_task_type)
                self.server_idle_event[available_task_type].clear()
            return None

    async def check_server(self, server: Server):
        start_time = time.time()
        backoff = 1
        for i in range(3):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{server.ip}", timeout=2, follow_redirects=True
                    )
                    # Any response indicates server is up
                    return True
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if i < 2:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                logger.error(f"check_server: 服务器({server})异常：{str(e)}")
            except Exception as e:
                logger.error(f"check_server: 服务器({server})异常：{e}")
                return False
        await program_manager.record_operation_time("check_server", start_time)
        return True

    async def release_server(self, server: Server):
        async with self._lock:
            if server not in self.running_servers:
                return False
            if server.status == ServerStatus.error:
                return False
            self.set_server_status(server, ServerStatus.idle)
            return True

    def set_server_status(self, server: Server, status: ServerStatus):
        server.status = status

        if status == ServerStatus.idle:
            for server_type in server.available_task_types:
                self._ensure_server_idle_event(server_type)
                self.server_idle_event[server_type].set()

        self._save_servers()
        return True

    async def add_running_server(
        self, ip: Union[str, None] = None, server_name: Union[str, None] = None
    ):
        start_time = time.time()
        async with self._lock:
            server = self.get_server_by_identifier(ip, server_name)
            if not server:
                logger.error(f"Server not found - ip:{ip} server_name:{server_name}")
                return False, f"ip:{ip} server_name:{server_name} 服务器不存在"

            if server in self.running_servers:
                logger.info(f"Server {server} is already running")
                return False, f"服务器{server}已经在运行"

            # Check server connectivity before adding
            if not await self.check_server(server):
                logger.error(f"Server {server} connection check failed")
                return False, f"服务器{server}连接检查失败"

            self.running_servers.append(server)
            self.set_server_status(server, ServerStatus.idle)

            program_manager.set_running_gpu_num(len(self.running_servers))
            await program_manager.record_operation_time(
                "add_running_server", start_time
            )
            return True, f"添加服务器{server} 成功"

    async def remove_running_server(
        self, ip: Union[str, None] = None, server_name: Union[str, None] = None
    ):
        start_time = time.time()
        async with self._lock:
            server = self.get_server_by_identifier(ip, server_name)
            if not server:
                logger.error(f"Server not found - ip:{ip} server_name:{server_name}")
                return False, f"ip:{ip} server_name:{server_name} 服务器不存在"

            if server not in self.running_servers:
                return False, f"服务器{server}不在运行"

            if server.status != ServerStatus.idle:
                return False, f"服务器{server}有任务在执行，不在空闲状态，请稍后再关闭"

            self.running_servers.remove(server)
            self.set_server_status(server, ServerStatus.stop)

            program_manager.set_running_gpu_num(len(self.running_servers))
            await program_manager.record_operation_time(
                "remove_running_server", start_time
            )
            return True, f"删除服务器{server} 成功"


# Create manager instance
server_manager = ServerManager()
