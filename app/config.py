"""
Configuration module for the AI Assistant application.
This centralizes all configuration settings including debug modes.
"""
import os
import logging
from typing import Dict, Any

# Debug flag - can be set via environment variable
DEBUG = os.environ.get("AI_ASSISTANT_DEBUG", "false").lower() in ("true", "1", "yes", "y")

# Additional configuration settings
CONFIG: Dict[str, Any] = {
    # Database settings
    "database": {
        "path": os.environ.get("AI_ASSISTANT_DB_PATH", "data/assistant.db")
    },
    
    # LMStudio settings
    "lmstudio": {
        "url": os.environ.get("LMSTUDIO_URL", "http://192.168.178.182:1234/v1")
    },
    
    # Server settings
    "server": {
        "host": os.environ.get("AI_ASSISTANT_HOST", "0.0.0.0"),
        "port": int(os.environ.get("AI_ASSISTANT_PORT", "8001")),
        "reload": os.environ.get("AI_ASSISTANT_RELOAD", "true").lower() in ("true", "1", "yes", "y")
    }
}

# Configure logging based on debug setting
def setup_logging():
    """Configure application-wide logging based on debug setting"""
    level = logging.DEBUG if DEBUG else logging.INFO
    
    # Format: detailed for debug mode, simpler for normal operation
    if DEBUG:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    else:
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Configure the root logger
    logging.basicConfig(
        level=level,
        format=log_format
    )
    
    # Create logger for this application
    logger = logging.getLogger("ai-assistant")
    logger.setLevel(level)
    
    # Suppress verbose logs from libraries unless in debug mode
    if not DEBUG:
        # Reduce verbosity of commonly noisy modules
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Return the logger for immediate use
    return logger

# Create a main application logger
logger = setup_logging()

# Log configuration on startup
def log_config():
    """Log the current configuration (only in debug mode)"""
    if DEBUG:
        logger.debug("Application Configuration:")
        logger.debug(f"Debug mode: {DEBUG}")
        logger.debug(f"Database path: {CONFIG['database']['path']}")
        logger.debug(f"LMStudio URL: {CONFIG['lmstudio']['url']}")
        logger.debug(f"Server host: {CONFIG['server']['host']}")
        logger.debug(f"Server port: {CONFIG['server']['port']}")
        logger.debug(f"Server reload: {CONFIG['server']['reload']}")
    else:
        logger.info("Starting application in normal mode (set AI_ASSISTANT_DEBUG=true for debug output)")