import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Track if root logger is configured
_root_configured = False


def setup_logging(modules_with_files=None, log_level=logging.INFO):
    """
    Setup logging with console handler and module-specific file handlers.
    
    Args:
        modules_with_files: List of module names that should have separate log files
        log_level: Logging level (default: INFO)
    """
    global _root_configured
    
    # Configure root logger only once (for console output)
    if not _root_configured:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Set to DEBUG to allow all levels
        
        # Console handler (shared by all modules)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        _root_configured = True
    
    # Add module-specific file handlers
    if modules_with_files:
        for module_name in modules_with_files:
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(log_level)
            
            # Check if this logger already has a file handler
            has_file_handler = any(
                isinstance(h, RotatingFileHandler) 
                for h in module_logger.handlers
            )
            
            if not has_file_handler:
                log_file = Path(f'log/log_files/{module_name}.log')
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = RotatingFileHandler(
                    str(log_file),
                    maxBytes=10*1024*1024,
                    backupCount=5
                )
                file_handler.setLevel(log_level)
                
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(formatter)
                module_logger.addHandler(file_handler)

if __name__ == "__main__":
    setup_logging()