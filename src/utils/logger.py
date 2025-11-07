import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

class AppLogger:
    """Centralized logger with console + rotating file output."""

    def __init__(self, name: str = "app", log_dir: str = "./logs", level: int = logging.INFO):
        self.name = name
        self.log_dir = log_dir
        self.level = level
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Configure the logger (console + file handlers)."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Avoid duplicate handlers if re-imported
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        self.logger.setLevel(self.level)

        # === Formatter ===
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # === File handler ===
        log_file = os.path.join(self.log_dir, f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)  # 5 MB
        file_handler.setFormatter(formatter)

        # === Console handler ===
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # === Add handlers ===
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    # === Shorthand helper methods ===
    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log an exception traceback (use inside except blocks)."""
        self.logger.exception(msg, *args, **kwargs)