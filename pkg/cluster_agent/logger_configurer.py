"""
Logger configurer helper module.
"""

import sys
import logging
from logging.handlers import RotatingFileHandler

class LoggerConfigurer:
    """
    Logger configurer for the collector log.
    """

    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024 # 10MB per log file
    FILE_BACKUP_COUNT = 1

    def __init__(
        self,
        log_format: str,
        log_file_path: str,
        logger: logging.Logger = None
    ):
        """
        :param logger: logger to configure, defauls to the root logger.
        """
        self.log_format = log_format
        self.log_file_path = log_file_path
        self.log_file_handler = None
        self.output_handler = None
        self.logger = logging.getLogger() if not logger else logger

    def configure_logger(self, is_debug: bool):
        """
        Configures the logger handlers with the log format & level.
        Configure 2 handlers:
        - 1 output handler (stdout), level set by given param `is_debug`
        - 1 file handler, level set to logging.DEBUG
        """
        formatter = logging.Formatter(self.log_format)
        self.log_file_handler = RotatingFileHandler(
            self.log_file_path,
            maxBytes=self.MAX_LOG_FILE_SIZE,
            backupCount=self.FILE_BACKUP_COUNT
        )
        self.output_handler = logging.StreamHandler(sys.stdout)
        self.output_handler.level = logging.DEBUG if is_debug else logging.INFO
        self.log_file_handler.level = logging.DEBUG
        self.logger.setLevel(logging.DEBUG)
        for handler in (self.log_file_handler, self.output_handler):
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def update_logger_level(self, is_debug: bool):
        """
        Updates the logger level. Updates only the stdout handler as the file handler
        always set to logging.DEBUG
        """
        self.output_handler.level = logging.DEBUG if is_debug else logging.INFO
