import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict
from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        # Include exception info if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def configure_logger(name: str = "FitOS") -> logging.Logger:
    """Configures and returns a logger instance with file and console handlers."""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if already configured
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(settings.LOG_LEVEL)
    
    # Console Handler: human-readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s (%(module)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler: structured JSON logs for backend analysis
    try:
        file_handler = logging.FileHandler(settings.LOG_FILE, encoding="utf-8")
        file_handler.setLevel(settings.LOG_LEVEL)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback if log file cannot be created
        logger.warning(f"Could not initialize file logging handler: {str(e)}")
        
    return logger


# Expose default logger
logger = configure_logger()
