import logging

from task_weaver.log.logger import configure_logging

logger = configure_logging(enabled=True, log_dir="./1logs/", level=logging.DEBUG)
