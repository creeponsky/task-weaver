from ..models.server_models import ProgramInfo, TaskTypeStats, ServerOperationStats
from ..utils.cache import CacheManager, CacheType
from ..log.logger import logger
import time
class ProgramManager:
    def __init__(self):
        logger.info("Initializing ProgramManager...")
        self.start_time = int(time.time())
        self.cache_manager = CacheManager("program_cache", CacheType.PROGRAM)
        self.info = self._load_info()
        # Initialize task type statistics if not present
        if not hasattr(self.info, 'first_start_time') or self.info.first_start_time == 0:
            logger.info("First time running - initializing first_start_time")
            self.info.first_start_time = self.start_time
            
        self._save_info()
        logger.info(f"ProgramManager initialized. First start time: {self.info.first_start_time}")

    def _load_info(self) -> ProgramInfo:
        """Load program info from cache"""
        try:
            data = self.cache_manager.read_cache()
            if data:
                logger.info("Loading existing program info from cache")
                return ProgramInfo(**data)
        except Exception as e:
            logger.error(f"Error loading cache: {str(e)}")
            
        logger.info("Creating new program info")
        return ProgramInfo(
            gpu_num=0,
            running_gpu_num=0,
            running_time=0,
            finished_task_num=0,
            failed_task_num=0,
            first_start_time=0,
            task_type_stats={},
            server_task_stats={},
            server_operation_stats={}
        )

    def _save_info(self):
        """Save program info to cache"""
        try:
            data = self.info.model_dump()
            self.cache_manager.write_cache(data)
        except Exception as e:
            logger.error(f"Error saving program info to cache: {str(e)}")

    def get_info(self):
        running_time = int(time.time()) - self.start_time
        self.info.running_time = int(running_time)
        return self.info
    
    async def record_task_time(self, task_type: str, start_time: float):
        duration_ms = (time.time() - start_time) * 1000
        if task_type not in self.info.server_task_stats:
            self.info.server_task_stats[task_type] = ServerOperationStats()
        self.info.server_task_stats[task_type].update_stats(duration_ms)
        self._save_info()

    async def record_operation_time(self, operation_name: str, start_time: float):
        duration_ms = (time.time() - start_time) * 1000
        if operation_name not in self.info.server_operation_stats:
            self.info.server_operation_stats[operation_name] = ServerOperationStats()
        self.info.server_operation_stats[operation_name].update_stats(duration_ms)
        self._save_info()
    
    def set_running_gpu_num(self, num):
        if not isinstance(num, int) or num < 0:
            logger.error(f"Invalid GPU number: {num}. Must be non-negative integer.")
            return
        self.info.running_gpu_num = num
        self._save_info()
        logger.info(f"Updated running GPU number to {num}")
    
    def set_gpu_num(self, num):
        if not isinstance(num, int) or num < 0:
            logger.error(f"Invalid GPU number: {num}. Must be non-negative integer.")
            return
        self.info.gpu_num = num
        self._save_info()
        logger.info(f"Updated total GPU number to {num}")
    
    def update_finished_task_num(self, task_type: str = None, duration: float = 0):
        self.info.finished_task_num += 1
        
        if task_type:
            if task_type not in self.info.task_type_stats:
                logger.info(f"Initializing stats for new task type: {task_type}")
                self.info.task_type_stats[task_type] = TaskTypeStats(
                    total=0, success=0, failed=0, avg_duration=0
                )
                
            stats = self.info.task_type_stats[task_type]
            stats.total += 1
            stats.success += 1
            
            # Update average duration
            old_avg = stats.avg_duration
            stats.avg_duration = (old_avg * (stats.success - 1) + duration) / stats.success
            logger.info(f"Task type {task_type} completed successfully. New average duration: {stats.avg_duration:.2f}s")
            
        self._save_info()

    def update_failed_task_num(self, task_type: str = None):
        self.info.failed_task_num += 1
        
        if task_type:
            if task_type not in self.info.task_type_stats:
                logger.info(f"Initializing stats for new task type: {task_type}")
                self.info.task_type_stats[task_type] = TaskTypeStats(
                    total=0, success=0, failed=0, avg_duration=0
                )
                
            stats = self.info.task_type_stats[task_type]
            stats.total += 1
            stats.failed += 1
            logger.info(f"Task type {task_type} failed. Total failures: {stats.failed}")
            
        self._save_info()

    def get_task_type_stats(self, task_type: str = None):
        """Get statistics for specific task type or all task types"""
        if task_type:
            if task_type not in self.info.task_type_stats:
                logger.info(f"No stats found for task type: {task_type}")
                return None
            return self.info.task_type_stats.get(task_type)
        return self.info.task_type_stats

program_manager = ProgramManager()