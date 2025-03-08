"""
Main entry point for the AI Assistant application.
Run this script to start the server.
"""
import uvicorn
import os
import sys
from app.config import CONFIG, DEBUG, logger, log_config

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

if __name__ == "__main__":
    # Log configuration on startup
    log_config()
    
    # Welcome message
    logger.info("Starting AI Assistant Framework...")
    
    if DEBUG:
        logger.debug("Debug mode is ENABLED - verbose logging active")
    
    logger.info(f"Make sure LMStudio is running with API server enabled at {CONFIG['lmstudio']['url']}")
    
    try:
        # Start the server with the correct import path for main:app
        uvicorn.run(
            "app.main:app", 
            host=CONFIG["server"]["host"], 
            port=CONFIG["server"]["port"], 
            reload=CONFIG["server"]["reload"],
            log_level="debug" if DEBUG else "info"
        )
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=DEBUG)
        sys.exit(1)