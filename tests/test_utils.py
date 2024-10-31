import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


def setup_logger(name, log_dir, level=logging.INFO):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    # Add a timestamp to the log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
    
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7, encoding='utf-8')
    file_handler.suffix = "%Y-%m-%d.log" # 更改日志文件名后缀，添加.log
    file_handler.setFormatter(formatter)
    file_handler.encoding = "utf-8"

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

log_directory = "logs"
logger = setup_logger("test_task_queue", log_directory)