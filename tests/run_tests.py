import asyncio

import pytest
from task_weaver.log.logger import configure_logging
import logging
configure_logging(enabled=True, log_dir="./logs/test/", level=logging.DEBUG)


async def main():
    # 这里可以添加断点进行调试
    pytest.main(["-v", "-s", "tests/"])

if __name__ == "__main__":
    asyncio.run(main()) 
    