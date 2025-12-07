"""
Logging Configuration

Sets up Python logging with rotating file handler for the application.
"""
import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_dir: Path = None, log_level: int = logging.INFO):
    """
    Set up application-wide logging with rotating file handler.
    
    Args:
        log_dir: Directory for log files (defaults to ~/.config/panapitouch/logs)
        log_level: Logging level (default: INFO)
    """
    if log_dir is None:
        # Default to ~/.config/panapitouch/logs
        config_dir = Path.home() / ".config" / "panapitouch"
        log_dir = config_dir / "logs"
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Log file path
    log_file = log_dir / "panapitouch.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create rotating file handler (10MB max, keep 5 backup files)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Create console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger('PyQt6').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)




