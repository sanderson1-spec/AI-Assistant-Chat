"""
Main entry point for the AI Assistant application.
Run this script to start the server.
"""
import uvicorn
import os
import sys
import multiprocessing
import logging
from app.config import CONFIG, DEBUG, logger

def setup_multiprocessing():
    """Set up multiprocessing based on platform"""
    try:
        if sys.platform == 'darwin':
            # Use 'fork' on macOS
            multiprocessing.set_start_method('fork')
            logger.info("Set multiprocessing start method to 'fork' on macOS")
        else:
            # Use 'spawn' on other platforms (Windows, Linux)
            multiprocessing.set_start_method('spawn')
            logger.info(f"Set multiprocessing start method to 'spawn' on {sys.platform}")
    except RuntimeError as e:
        # If context has already been set, just log it
        logger.info(f"Multiprocessing context already set: {str(e)}")

def ensure_directories():
    """Ensure all required directories exist"""
    directories = [
        "data",
        "data/personalities",
        "data/memories",
        "data/vector_db",
        "data/conversations"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")

def main():
    """Main entry point for the application"""
    # Welcome message
    logger.info("Starting AI Assistant Framework...")
    
    if DEBUG:
        logger.debug("Debug mode is ENABLED - verbose logging active")
    
    # Set up multiprocessing
    setup_multiprocessing()
    
    # Ensure directories exist
    ensure_directories()
    
    # Log LMStudio requirement
    logger.info(f"Make sure LMStudio is running with API server enabled at {CONFIG['lmstudio']['url']}")
    
    try:
        # Configure uvicorn with minimal settings
        config = uvicorn.Config(
            "app.main:app",
            host=CONFIG["server"]["host"],
            port=CONFIG["server"]["port"],
            log_level="debug" if DEBUG else "info",
            reload=False,  # Disable reload to avoid multiprocessing issues
            workers=1
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=DEBUG)
        sys.exit(1)

if __name__ == "__main__":
    main()