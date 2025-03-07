"""
Extensions to the Database class for AI Agents support.
This extends the core Database class with methods for tasks, notifications, bots, etc.
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# These methods will be integrated into your existing Database class
class DatabaseAgentExtensions:
    """
    Extension methods for the Database class to support AI Agents
    These methods will be added to the existing Database class
    """
    
    # Task-related methods
    
    async def store_task(
        self, 
        task_id: str,
        user_id: str,
        bot_id: str,
        task_type: str,
        execute_at: str,
        params: str,
        recurring: bool = False,
        interval: Optional[int] = None
    ) -> bool:
        """Store a scheduled task in the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            created_at = datetime.utcnow().isoformat()
            
            cursor.execute("""
            INSERT INTO tasks
            (id, user_id, bot_id, task_type, execute_at, params, recurring, interval, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                user_id,
                bot_id,
                task_type,
                execute_at,
                params,
                1 if recurring else 0,
                interval,
                created_at
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error storing task: {e}")
            return False
        finally:
            conn.close()
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM tasks WHERE id = ?
        """, (task_id,))
        
        task_row = cursor.fetchone()
        conn.close()
        
        if not task_row:
            return None
        
        # Convert to dict
        columns = [col[0] for col in cursor.description]
        task = dict(zip(columns, task_row))
        
        # Convert boolean
        task['recurring'] = bool(task['recurring'])
        
        return task
    
    async def update_task_execution_time(self, task_id: str, execution_time: str) -> bool:
        """Update the last execution time for a task"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            UPDATE tasks
            SET last_executed_at = ?
            WHERE id = ?
            """, (execution_time, task_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating task execution time: {e}")
            return False
        finally:
            conn.close()
    
    async def remove_task(self, task_id: str) -> bool:
        """Remove a task from the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            DELETE FROM tasks WHERE id = ?
            """, (task_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing task: {e}")
            return False
        finally:
            conn.close()
    
    async def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM tasks ORDER BY execute_at
        """)
        
        tasks = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for task_row in tasks:
            task = dict(zip(columns, task_row))
            task['recurring'] = bool(task['recurring'])
            result.append(task)
        
        return result
    
    async def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get tasks for a specific user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM tasks WHERE user_id = ? ORDER BY execute_at
        """, (user_id,))
        
        tasks = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for task_row in tasks:
            task = dict(zip(columns, task_row))
            task['recurring'] = bool(task['recurring'])
            result.append(task)
        
        return result
    
    # Notification-related methods
    
    async def store_notification(
        self,
        user_id: str,
        message: str,
        source_bot_id: Optional[str] = None,
        metadata: Optional[str] = None,
        scheduled_for: Optional[str] = None,
        delivered_at: Optional[str] = None
    ) -> int:
        """Store a notification in the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            created_at = datetime.utcnow().isoformat()
            
            cursor.execute("""
            INSERT INTO notifications
            (user_id, message, source_bot_id, metadata, scheduled_for, delivered_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                message,
                source_bot_id,
                metadata,
                scheduled_for,
                delivered_at,
                created_at
            ))
            
            notification_id = cursor.lastrowid
            conn.commit()
            return notification_id
        except Exception as e:
            print(f"Error storing notification: {e}")
            return -1
        finally:
            conn.close()
    
    async def get_notification(self, notification_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific notification by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM notifications WHERE id = ?
        """, (notification_id,))
        
        notification_row = cursor.fetchone()
        conn.close()
        
        if not notification_row:
            return None
        
        # Convert to dict
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, notification_row))
    
    async def mark_notification_delivered(self, notification_id: int, delivered_at: str) -> bool:
        """Mark a notification as delivered"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            UPDATE notifications
            SET delivered_at = ?
            WHERE id = ?
            """, (delivered_at, notification_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error marking notification as delivered: {e}")
            return False
        finally:
            conn.close()
    
    async def mark_notification_read(self, notification_id: int, read_at: str) -> bool:
        """Mark a notification as read"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
            UPDATE notifications
            SET read_at = ?
            WHERE id = ?
            """, (read_at, notification_id))
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return False
        finally:
            conn.close()
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        include_read: bool = False, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get notifications for a specific user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if include_read:
            cursor.execute("""
            SELECT * FROM notifications 
            WHERE user_id = ? 
            ORDER BY created_at DESC
            LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
            SELECT * FROM notifications 
            WHERE user_id = ? AND (read_at IS NULL OR read_at = '')
            ORDER BY created_at DESC
            LIMIT ?
            """, (user_id, limit))
        
        notifications = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for notification_row in notifications:
            result.append(dict(zip(columns, notification_row)))
        
        return result
    
    # Bot data storage methods
    
    async def store_bot_data(self, bot_id: str, user_id: str, key: str, value: str) -> bool:
        """Store bot-specific data for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            updated_at = datetime.utcnow().isoformat()
            
            # First try to update, then insert if no row exists
            cursor.execute("""
            UPDATE bot_data
            SET value = ?, updated_at = ?
            WHERE bot_id = ? AND user_id = ? AND key = ?
            """, (value, updated_at, bot_id, user_id, key))
            
            if cursor.rowcount == 0:
                # Insert new row
                cursor.execute("""
                INSERT INTO bot_data
                (bot_id, user_id, key, value, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """, (bot_id, user_id, key, value, updated_at))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error storing bot data: {e}")
            return False
        finally:
            conn.close()
    
    async def get_bot_data(self, bot_id: str, user_id: str, key: str) -> Optional[str]:
        """Get bot-specific data for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT value FROM bot_data 
        WHERE bot_id = ? AND user_id = ? AND key = ?
        """, (bot_id, user_id, key))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    async def get_all_bot_data(self, bot_id: str, user_id: str) -> Dict[str, str]:
        """Get all bot-specific data for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT key, value FROM bot_data 
        WHERE bot_id = ? AND user_id = ?
        """, (bot_id, user_id))
        
        results = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in results}
    
    # Bot preferences methods
    
    async def store_bot_preferences(
        self, 
        user_id: str, 
        bot_id: str, 
        enabled: bool = True,
        settings: Optional[str] = None
    ) -> bool:
        """Store user preferences for a specific bot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            updated_at = datetime.utcnow().isoformat()
            
            # First try to update, then insert if no row exists
            cursor.execute("""
            UPDATE bot_preferences
            SET enabled = ?, settings = ?, updated_at = ?
            WHERE user_id = ? AND bot_id = ?
            """, (1 if enabled else 0, settings, updated_at, user_id, bot_id))
            
            if cursor.rowcount == 0:
                # Insert new row
                cursor.execute("""
                INSERT INTO bot_preferences
                (user_id, bot_id, enabled, settings, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """, (user_id, bot_id, 1 if enabled else 0, settings, updated_at))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error storing bot preferences: {e}")
            return False
        finally:
            conn.close()
    
    async def get_bot_preferences(self, user_id: str, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences for a specific bot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM bot_preferences 
        WHERE user_id = ? AND bot_id = ?
        """, (user_id, bot_id))
        
        pref_row = cursor.fetchone()
        conn.close()
        
        if not pref_row:
            return None
        
        # Convert to dict
        columns = [col[0] for col in cursor.description]
        prefs = dict(zip(columns, pref_row))
        
        # Convert boolean
        prefs['enabled'] = bool(prefs['enabled'])
        
        return prefs
    
    async def get_user_bot_preferences(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all bot preferences for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM bot_preferences 
        WHERE user_id = ?
        """, (user_id,))
        
        pref_rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for pref_row in pref_rows:
            prefs = dict(zip(columns, pref_row))
            prefs['enabled'] = bool(prefs['enabled'])
            result.append(prefs)
        
        return result
    
    # Conversation context methods
    
    async def store_conversation_context(self, conversation_id: str, context: Dict[str, Any]) -> bool:
        """Store context data for a conversation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            updated_at = datetime.utcnow().isoformat()
            context_json = json.dumps(context)
            
            # First try to update, then insert if no row exists
            cursor.execute("""
            UPDATE conversation_context
            SET context = ?, updated_at = ?
            WHERE conversation_id = ?
            """, (context_json, updated_at, conversation_id))
            
            if cursor.rowcount == 0:
                # Insert new row
                cursor.execute("""
                INSERT INTO conversation_context
                (conversation_id, context, updated_at)
                VALUES (?, ?, ?)
                """, (conversation_id, context_json, updated_at))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error storing conversation context: {e}")
            return False
        finally:
            conn.close()
    
    async def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get context data for a conversation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT context FROM conversation_context 
        WHERE conversation_id = ?
        """, (conversation_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        else:
            return {}
    
    async def update_conversation_context(self, conversation_id: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in conversation context"""
        # Get current context
        current_context = await self.get_conversation_context(conversation_id)
        
        # Apply updates
        current_context.update(updates)
        
        # Store the updated context
        return await self.store_conversation_context(conversation_id, current_context)