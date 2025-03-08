import sqlite3
import json
from datetime import datetime
import os
from typing import Dict, List, Any, Optional

class Database:
    def __init__(self, db_path="assistant.db"):
        self.db_path = db_path
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.initialize_db()
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    def initialize_db(self):
        """Initialize the database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Messages table with support for edited messages and versions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL,
            role TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            parent_id INTEGER,
            is_edited INTEGER DEFAULT 0,
            version INTEGER DEFAULT 1,
            is_active_version INTEGER DEFAULT 1,
            metadata TEXT
        )
        """)
        
        # Conversations table for metadata
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Scheduled tasks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            execute_at TEXT NOT NULL,
            params TEXT NOT NULL,
            recurring INTEGER DEFAULT 0,
            interval INTEGER,
            last_executed_at TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        # Notifications table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            source_bot_id TEXT,
            metadata TEXT,
            scheduled_for TEXT,
            delivered_at TEXT,
            read_at TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        # Bot data storage (for specialized bot state)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_data (
            bot_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (bot_id, user_id, key)
        )
        """)
        
        # User bot preferences
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_preferences (
            user_id TEXT NOT NULL,
            bot_id TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            settings TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, bot_id)
        )
        """)
        
        # Conversation context storage
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_context (
            conversation_id TEXT PRIMARY KEY,
            context TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
    # Core message methods
    
    async def store_message(self, user_id, content, role, conversation_id=None, parent_id=None, version=1, metadata=None):
        """Store a message in the database"""
        timestamp = datetime.utcnow().isoformat()
        
        # Generate a conversation ID if not provided
        if conversation_id is None:
            conversation_id = f"conv_{timestamp}_{user_id}"
            # Create a new conversation
            await self.create_conversation(conversation_id, user_id)
        else:
            # Update conversation timestamp
            await self.update_conversation_timestamp(conversation_id)
            
        # Store in database
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO messages 
        (user_id, timestamp, content, role, conversation_id, parent_id, version, metadata) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, 
            timestamp, 
            content, 
            role, 
            conversation_id,
            parent_id,
            version,
            json.dumps(metadata) if metadata else None
        ))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return message_id, conversation_id
    
    async def edit_message(self, message_id, new_content):
        """Edit an existing message and mark it as edited"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE messages
        SET content = ?, is_edited = 1
        WHERE id = ?
        """, (new_content, message_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    async def delete_message(self, message_id):
        """Delete a message and its responses from the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # First get message info to determine if it's a user or assistant message
            cursor.execute(
                "SELECT role, conversation_id FROM messages WHERE id = ?", 
                (message_id,)
            )
            message_info = cursor.fetchone()
            
            if not message_info:
                # Message not found
                cursor.execute("ROLLBACK")
                return False
                
            role, conversation_id = message_info
            
            if role == 'user':
                # If it's a user message, also delete all its responses
                cursor.execute(
                    "DELETE FROM messages WHERE parent_id = ?", 
                    (message_id,)
                )
                
            # Delete the message itself
            cursor.execute(
                "DELETE FROM messages WHERE id = ?", 
                (message_id,)
            )
            
            # Update conversation timestamp
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (datetime.utcnow().isoformat(), conversation_id)
            )
            
            # Commit the transaction
            cursor.execute("COMMIT")
            print(f"Message {message_id} deleted successfully")
            return True
        except Exception as e:
            # Rollback in case of error
            cursor.execute("ROLLBACK")
            print(f"Error deleting message: {e}")
            return False
        finally:
            conn.close()
    
    async def rewind_to_message(self, message_id):
        """
        Rewind conversation by deleting all messages after the specified message
        Returns the conversation_id for the rewound conversation
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Get message info including timestamp and conversation
            cursor.execute(
                "SELECT timestamp, conversation_id FROM messages WHERE id = ?", 
                (message_id,)
            )
            message_info = cursor.fetchone()
            
            if not message_info:
                # Message not found
                cursor.execute("ROLLBACK")
                return None
                
            timestamp, conversation_id = message_info
            
            # Delete all later messages
            cursor.execute("""
            DELETE FROM messages 
            WHERE conversation_id = ? AND timestamp > ?
            """, (conversation_id, timestamp))
            
            # Update conversation timestamp
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (datetime.utcnow().isoformat(), conversation_id)
            )
            
            # Commit the transaction
            cursor.execute("COMMIT")
            print(f"Rewound conversation to message {message_id} (deleted all later messages)")
            return conversation_id
        except Exception as e:
            # Rollback in case of error
            cursor.execute("ROLLBACK")
            print(f"Error rewinding conversation: {e}")
            return None
        finally:
            conn.close()
    
    async def store_response_version(self, user_id, content, parent_id, conversation_id, version=1, make_active=True):
        """Store a new version of a response"""
        # If making this the active version, deactivate all other versions for this parent
        if make_active:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            UPDATE messages
            SET is_active_version = 0
            WHERE parent_id = ? AND role = 'assistant'
            """, (parent_id,))
            
            conn.commit()
            conn.close()
        
        # Store the new response version
        message_id, _ = await self.store_message(
            user_id=user_id,
            content=content,
            role="assistant",
            conversation_id=conversation_id,
            parent_id=parent_id,
            version=version
        )
        
        return message_id
    
    async def get_response_versions(self, parent_id):
        """Get all response versions for a specific user message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, content, version, is_active_version, timestamp
        FROM messages
        WHERE parent_id = ? AND role = 'assistant'
        ORDER BY version ASC
        """, (parent_id,))
        
        versions = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0],
            "content": row[1],
            "version": row[2],
            "is_active": bool(row[3]),
            "timestamp": row[4]
        } for row in versions]
    
    async def set_active_response_version(self, message_id, parent_id):
        """Set a specific response version as the active one"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Deactivate all versions for this parent
            cursor.execute("""
            UPDATE messages
            SET is_active_version = 0
            WHERE parent_id = ? AND role = 'assistant'
            """, (parent_id,))
            
            # Activate the specified version
            cursor.execute("""
            UPDATE messages
            SET is_active_version = 1
            WHERE id = ?
            """, (message_id,))
            
            # Commit the transaction
            cursor.execute("COMMIT")
            return True
        except Exception as e:
            # Rollback in case of error
            cursor.execute("ROLLBACK")
            print(f"Error setting active version: {e}")
            return False
        finally:
            conn.close()
    
    async def create_conversation(self, conversation_id, user_id, title=None):
        """Create a new conversation"""
        timestamp = datetime.utcnow().isoformat()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO conversations
        (conversation_id, user_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            conversation_id,
            user_id,
            title or f"Conversation {timestamp}",
            timestamp,
            timestamp
        ))
        
        conn.commit()
        conn.close()
    
    async def update_conversation_timestamp(self, conversation_id):
        """Update the updated_at timestamp for a conversation"""
        timestamp = datetime.utcnow().isoformat()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE conversations
        SET updated_at = ?
        WHERE conversation_id = ?
        """, (timestamp, conversation_id))
        
        conn.commit()
        conn.close()
    
    async def get_conversation_history(self, conversation_id, limit=100):
        """Get messages from a specific conversation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all messages but filter out inactive response versions
        cursor.execute("""
        SELECT m.id, m.user_id, m.timestamp, m.content, m.role, m.parent_id, m.is_edited, m.version, m.metadata
        FROM messages m
        WHERE m.conversation_id = ? AND (m.role != 'assistant' OR m.is_active_version = 1)
        ORDER BY m.timestamp ASC
        LIMIT ?
        """, (conversation_id, limit))
        
        messages = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0],
            "user_id": row[1],
            "timestamp": row[2],
            "content": row[3],
            "role": row[4],
            "parent_id": row[5],
            "is_edited": bool(row[6]),
            "version": row[7],
            "metadata": json.loads(row[8]) if row[8] else None
        } for row in messages]
    
    async def get_recent_conversations(self, user_id, limit=10):
        """Get recent conversations for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT conversation_id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """, (user_id, limit))
        
        conversations = cursor.fetchall()
        conn.close()
        
        return [{
            "conversation_id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3]
        } for row in conversations]
    
    async def delete_conversation(self, conversation_id):
        """Delete a conversation and all its messages from the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Delete messages first (due to foreign key relationship)
            cursor.execute(
                "DELETE FROM messages WHERE conversation_id = ?", 
                (conversation_id,)
            )
            
            # Delete the conversation
            cursor.execute(
                "DELETE FROM conversations WHERE conversation_id = ?", 
                (conversation_id,)
            )
            
            # Commit the transaction
            cursor.execute("COMMIT")
            print(f"Conversation {conversation_id} deleted successfully")
            return True
        except Exception as e:
            # Rollback in case of error
            cursor.execute("ROLLBACK")
            print(f"Error deleting conversation: {e}")
            return False
        finally:
            conn.close()

    async def clear_all_conversations(self, user_id):
        """Delete all conversations for a specific user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Get all conversation IDs for this user
            cursor.execute(
                "SELECT conversation_id FROM conversations WHERE user_id = ?", 
                (user_id,)
            )
            conversation_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete messages for all these conversations
            cursor.execute(
                "DELETE FROM messages WHERE conversation_id IN "
                "(SELECT conversation_id FROM conversations WHERE user_id = ?)", 
                (user_id,)
            )
            
            # Delete the conversations
            cursor.execute(
                "DELETE FROM conversations WHERE user_id = ?", 
                (user_id,)
            )
            
            # Commit the transaction
            cursor.execute("COMMIT")
            print(f"Deleted {len(conversation_ids)} conversations for user {user_id}")
            return len(conversation_ids)
        except Exception as e:
            # Rollback in case of error
            cursor.execute("ROLLBACK")
            print(f"Error clearing conversations: {e}")
            return 0
        finally:
            conn.close()
    
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
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for task_row in tasks:
            task = dict(zip(columns, task_row))
            task['recurring'] = bool(task['recurring'])
            result.append(task)
        
        conn.close()
        return result
    
    async def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get tasks for a specific user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT * FROM tasks WHERE user_id = ? ORDER BY execute_at
        """, (user_id,))
        
        tasks = cursor.fetchall()
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for task_row in tasks:
            task = dict(zip(columns, task_row))
            task['recurring'] = bool(task['recurring'])
            result.append(task)
        
        conn.close()
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
        
        if not notification_row:
            conn.close()
            return None
        
        # Convert to dict
        columns = [col[0] for col in cursor.description]
        notification = dict(zip(columns, notification_row))
        conn.close()
        return notification
    
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
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for notification_row in notifications:
            result.append(dict(zip(columns, notification_row)))
        
        conn.close()
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
        
        if not pref_row:
            conn.close()
            return None
        
        # Convert to dict
        columns = [col[0] for col in cursor.description]
        prefs = dict(zip(columns, pref_row))
        
        # Convert boolean
        prefs['enabled'] = bool(prefs['enabled'])
        
        conn.close()
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
        
        # Convert to list of dicts
        columns = [col[0] for col in cursor.description]
        result = []
        
        for pref_row in pref_rows:
            prefs = dict(zip(columns, pref_row))
            prefs['enabled'] = bool(prefs['enabled'])
            result.append(prefs)
        
        conn.close()
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