"""
Notification Service for AI Assistant
Handles sending notifications to users through various channels
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

class NotificationService:
    """Service to manage and deliver notifications to users"""
    
    def __init__(self, database, websocket_manager, task_scheduler=None):
        self.database = database
        self.websocket_manager = websocket_manager
        # Will be set after TaskScheduler is created to avoid circular dependencies
        self.task_scheduler = task_scheduler  
        self.logger = logging.getLogger("ai-assistant.notification-service")
    
    def set_task_scheduler(self, task_scheduler):
        """Set the task scheduler (called after initialization)"""
        self.task_scheduler = task_scheduler
    
    async def send_notification(
        self, 
        user_id: str, 
        message: str, 
        source_bot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Send an immediate notification to a user
        
        Args:
            user_id: ID of the user to notify
            message: Notification message
            source_bot_id: ID of the bot sending the notification
            metadata: Additional metadata for the notification
            
        Returns:
            Notification ID
        """
        self.logger.info(f"Sending notification to user {user_id}")
        
        # Store notification in database
        notification_id = await self.database.store_notification(
            user_id=user_id,
            message=message,
            source_bot_id=source_bot_id,
            metadata=json.dumps(metadata) if metadata else None,
            delivered_at=datetime.now().isoformat()
        )
        
        # Send via WebSocket if user is connected
        client_ids = self.websocket_manager.get_client_ids_for_user(user_id)
        for client_id in client_ids:
            await self.websocket_manager.send_message(client_id, {
                "type": "notification",
                "id": notification_id,
                "message": message,
                "source_bot_id": source_bot_id,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            })
        
        self.logger.info(f"Notification {notification_id} sent to {len(client_ids)} clients")
        return notification_id
    
    async def schedule_notification(
        self, 
        user_id: str, 
        message: str, 
        send_at: datetime,
        source_bot_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Schedule a notification for future delivery
        
        Args:
            user_id: ID of the user to notify
            message: Notification message
            send_at: When to send the notification
            source_bot_id: ID of the bot sending the notification
            metadata: Additional metadata for the notification
            
        Returns:
            Notification ID
        """
        self.logger.info(f"Scheduling notification for user {user_id} at {send_at}")
        
        # Store in database
        notification_id = await self.database.store_notification(
            user_id=user_id,
            message=message,
            source_bot_id=source_bot_id,
            metadata=json.dumps(metadata) if metadata else None,
            scheduled_for=send_at.isoformat(),
            delivered_at=None
        )
        
        # Schedule task for delivery
        if self.task_scheduler:
            await self.task_scheduler.schedule_task(
                task_type="deliver_notification",
                bot_id="notification_service",  # Special internal bot ID
                user_id=user_id,
                execute_at=send_at,
                params={
                    "notification_id": notification_id
                }
            )
        else:
            self.logger.warning("Task scheduler not available, notification will not be delivered automatically")
        
        return notification_id
    
    async def deliver_scheduled_notification(self, notification_id: int) -> bool:
        """
        Deliver a previously scheduled notification
        
        Args:
            notification_id: ID of the notification to deliver
            
        Returns:
            True if delivered successfully, False otherwise
        """
        # Get notification from database
        notification = await self.database.get_notification(notification_id)
        
        if not notification:
            self.logger.error(f"Notification {notification_id} not found")
            return False
        
        # Check if it's already been delivered
        if notification.get("delivered_at"):
            self.logger.info(f"Notification {notification_id} already delivered at {notification['delivered_at']}")
            return True
        
        # Send the notification
        user_id = notification["user_id"]
        message = notification["message"]
        source_bot_id = notification.get("source_bot_id")
        metadata = json.loads(notification["metadata"]) if notification.get("metadata") else None
        
        # Send via WebSocket
        client_ids = self.websocket_manager.get_client_ids_for_user(user_id)
        for client_id in client_ids:
            await self.websocket_manager.send_message(client_id, {
                "type": "notification",
                "id": notification_id,
                "message": message,
                "source_bot_id": source_bot_id,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            })
        
        # Mark as delivered
        await self.database.mark_notification_delivered(
            notification_id, 
            datetime.now().isoformat()
        )
        
        self.logger.info(f"Scheduled notification {notification_id} delivered to {len(client_ids)} clients")
        return True
    
    async def mark_notification_read(self, notification_id: int) -> bool:
        """Mark a notification as read"""
        result = await self.database.mark_notification_read(
            notification_id, 
            datetime.now().isoformat()
        )
        return result
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        include_read: bool = False, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent notifications for a user"""
        notifications = await self.database.get_user_notifications(
            user_id, 
            include_read,
            limit
        )
        
        # Format notifications
        for notification in notifications:
            if notification.get("metadata"):
                notification["metadata"] = json.loads(notification["metadata"])
        
        return notifications