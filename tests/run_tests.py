import asyncio

import pytest
from test_utils import logger


async def main():
    logger.info("Starting tests...")
    # 这里可以添加断点进行调试
    pytest.main(["-v", "-s", "tests/"])

if __name__ == "__main__":
    asyncio.run(main()) 
    