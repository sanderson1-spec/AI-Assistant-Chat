"""
Script to schedule a check-in notification from Jess at 11:20 PM

This script directly inserts a scheduled notification into the database.
"""
import asyncio
import sys
import logging
import json
from datetime import datetime, timedelta
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("schedule-checkin")

async def schedule_jess_checkin_notification():
    """Schedule a check-in notification from Jess at 11:20 PM"""
    try:
        # Connect to the database directly
        conn = sqlite3.connect('assistant.db')
        cursor = conn.cursor()
        
        # User ID - typically this is identified in a real scenario
        user_id = "default_user"
        
        # Create a message from Jess
        message = "Hey there! It's 11:20 PM, just checking in as you requested. What would you like to talk about?"
        
        # Add metadata with Jess's character info
        metadata = {
            "type": "character_message",
            "character_name": "jess",
            "is_checkin": True,
            "priority": "high"
        }
        
        # Get the current time
        now = datetime.now()
        
        # Calculate next 11:20 PM
        target_time = now.replace(hour=23, minute=20, second=0, microsecond=0)
        if target_time < now:
            # If 11:20 PM today is in the past, schedule for tomorrow
            target_time = target_time + timedelta(days=1)
        
        logger.info(f"Scheduling check-in notification for {target_time}")
        
        # Insert the notification record
        created_at = datetime.now().isoformat()
        cursor.execute("""
        INSERT INTO notifications
        (user_id, message, source_bot_id, metadata, scheduled_for, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            message,
            "character_bot",
            json.dumps(metadata),
            target_time.isoformat(),
            created_at
        ))
        
        notification_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully scheduled check-in notification (ID: {notification_id}) for {target_time}")
        return notification_id
        
    except Exception as e:
        logger.error(f"Error scheduling Jess's check-in notification: {e}", exc_info=True)
        raise

async def main():
    """Main entry point for the script"""
    try:
        logger.info("Starting Jess check-in notification scheduling")
        notification_id = await schedule_jess_checkin_notification()
        logger.info(f"Successfully scheduled notification (ID: {notification_id})")
        
        print("\nCheck-in notification scheduled successfully!")
        print(f"Jess will send a notification at 11:20 PM")
        print("\nYou can verify this in the database admin page:")
        print("1. Go to the Database Admin page in the app")
        print("2. Select the 'notifications' table")
        print("3. Look for the notification with ID:", notification_id)
    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 