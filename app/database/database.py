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
        
        # Messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            content TEXT NOT NULL,
            role TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            metadata TEXT,
            message_id TEXT,
            version INTEGER DEFAULT 1
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
    
    async def store_message(self, user_id, content, role, conversation_id=None, metadata=None, message_id=None, is_regeneration=False, response_to_id=None):
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
        
        # Process metadata
        metadata_dict = metadata if metadata else {}
        
        # For assistant messages that are responses to user messages
        if role == 'assistant' and response_to_id:
            metadata_dict['responseToId'] = response_to_id
        
        # Generate a unique message ID if not provided
        if not message_id:
            message_id = f"msg_{timestamp}_{user_id}"
            
        version = 1
        if is_regeneration and role == 'assistant':
            # Find the highest version number for this message
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(version) FROM messages 
                WHERE message_id = ? AND role = 'assistant'
            """, (response_to_id,))
            result = cursor.fetchone()
            if result and result[0]:
                version = result[0] + 1
            conn.close()
        
        # Store in database
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO messages 
        (user_id, timestamp, content, role, conversation_id, metadata, message_id, version) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, 
            timestamp, 
            content, 
            role, 
            conversation_id,
            json.dumps(metadata_dict),
            message_id,
            version
        ))
        
        db_message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return db_message_id, conversation_id, message_id
    
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
    
    async def get_conversation_history(self, conversation_id, limit=100, include_all_versions=False):
        """Get messages from a specific conversation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if include_all_versions:
            # Include all message versions
            cursor.execute("""
            SELECT id, user_id, timestamp, content, role, metadata, message_id, version
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            """, (conversation_id,))
        else:
            # Only include the latest version of each message
            cursor.execute("""
            SELECT m1.id, m1.user_id, m1.timestamp, m1.content, m1.role, m1.metadata, m1.message_id, m1.version
            FROM messages m1
            JOIN (
                SELECT message_id, role, MAX(version) as max_version
                FROM messages
                WHERE conversation_id = ?
                GROUP BY message_id, role
            ) m2 ON m1.message_id = m2.message_id AND m1.version = m2.max_version AND m1.role = m2.role
            WHERE m1.conversation_id = ?
            ORDER BY m1.timestamp ASC
            """, (conversation_id, conversation_id))
        
        messages = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0],
            "user_id": row[1],
            "timestamp": row[2],
            "content": row[3],
            "role": row[4],
            "metadata": json.loads(row[5]) if row[5] else None,
            "message_id": row[6],
            "version": row[7]
        } for row in messages]
    
    async def get_message_versions(self, message_id, role='assistant'):
        """Get all versions of a specific message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, timestamp, content, version, metadata
        FROM messages
        WHERE message_id = ? AND role = ?
        ORDER BY version ASC
        """, (message_id, role))
        
        versions = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row[0],
            "timestamp": row[1],
            "content": row[2],
            "version": row[3],
            "metadata": json.loads(row[4]) if row[4] else None
        } for row in versions]
    
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