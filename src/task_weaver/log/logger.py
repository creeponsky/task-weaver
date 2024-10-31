import logging
import sys
from logging.handlers import TimedRotatingFileHandler
import os

class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    info = "\x1b[32m"  # Green
    warning = "\x1b[33m"  # Yellow 
    error = "\x1b[31m"  # Red
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.info + self.fmt + self.reset,
            logging.WARNING: self.warning + self.fmt + self.reset,
            logging.ERROR: self.error + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        # Add library prefix to the message
        record.msg = f"[TaskWeaver] {record.msg}"
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logger(name, log_dir=None, level=logging.INFO, enabled=True):
    logger = logging.getLogger(name)
    
    # Return if handlers already configured
    if logger.handlers:
        return logger
    
    # If logging is disabled, set level to CRITICAL+1 to disable all logging
    if not enabled:
        logger.setLevel(logging.CRITICAL + 1)
        return logger
        
    logger.setLevel(level)
    
    # Add console handler with color formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(console_handler)

    # Add file handler only if log_dir is specified
    if log_dir:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        log_file = os.path.join(log_dir, f"{name}.log")
        
        file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7, encoding='utf-8')
        file_handler.suffix = "%Y-%m-%d.log"
        file_handler.setFormatter(file_formatter)
        file_handler.encoding = "utf-8"
        logger.addHandler(file_handler)

    return logger

# Create default logger without file handler - disabled by default
logger = setup_logger("task_weaver", enabled=False)

def configure_logging(enabled=True, level=logging.INFO, log_dir=None):
    """
    Configure TaskWeaver logging settings.
    
    Args:
        enabled (bool): Whether to enable logging (default: True)
        level (int): Logging level (default: logging.INFO)
        log_dir (str, optional): Directory for log files
    """
    global logger
    logger = setup_logger("task_weaver", log_dir=log_dir, level=level, enabled=enabled)
    return logger
