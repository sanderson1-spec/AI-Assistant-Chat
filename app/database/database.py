import sqlite3
import json
from datetime import datetime
import os

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
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
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