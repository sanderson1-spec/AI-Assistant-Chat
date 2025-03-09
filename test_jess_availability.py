"""
Test script to have Jess proactively notify the user of her availability

This script simulates Jess sending a proactive message to let the user know she's available to talk.
It uses the NotificationService to schedule an immediate notification that will appear in the UI.
"""
import asyncio
import sys
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-jess-availability")

# Import required modules
try:
    from app.database.database import Database
    from app.websocket.enhanced_connection_manager import EnhancedConnectionManager
    from app.notifications.notification_service import NotificationService
    from app.tasks.task_scheduler import TaskScheduler
    from app.bots.bot_framework import BotRegistry
    logger.info("Successfully imported modules")
except ImportError as e:
    logger.error(f"Import error: {e}")
    print("Import error - make sure you're running this from the project root directory")
    sys.exit(1)

async def send_jess_availability_notification():
    """Send an immediate notification from Jess about her availability"""
    try:
        # Initialize dependencies
        db = Database()
        websocket_manager = EnhancedConnectionManager()
        bot_registry = BotRegistry(db)
        
        # Initialize services
        notification_service = NotificationService(db, websocket_manager)
        
        # User ID - typically this is identified in a real scenario
        user_id = "default_user"
        
        # Create a message from Jess
        message = "Hey there! Just wanted to let you know I'm available to chat now. What would you like to talk about?"
        
        # Add metadata with Jess's character info
        metadata = {
            "type": "character_message",
            "character_name": "jess",
            "is_availability_notification": True,
            "priority": "high"
        }
        
        # Send the notification immediately
        logger.info("Sending immediate notification from Jess")
        notification_id = await notification_service.send_notification(
            user_id=user_id,
            message=message,
            source_bot_id="character_bot",
            metadata=metadata
        )
        
        logger.info(f"Successfully sent notification (ID: {notification_id})")
        return notification_id
        
    except Exception as e:
        logger.error(f"Error sending Jess's availability notification: {e}", exc_info=True)
        raise

async def main():
    """Main entry point for the script"""
    try:
        logger.info("Starting Jess availability notification test")
        notification_id = await send_jess_availability_notification()
        logger.info(f"Successfully sent notification (ID: {notification_id})")
        
        print("\nNotification sent successfully!")
        print("To see this notification in the UI:")
        print("1. Make sure your application is running")
        print("2. Open the web interface in your browser")
        print("3. You should see Jess's message as a notification")
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 