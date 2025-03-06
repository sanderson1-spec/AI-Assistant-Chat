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
    
    async def store_message(self, user_id, content, role, conversation_id=None, metadata=None):
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
        (user_id, timestamp, content, role, conversation_id, metadata) 
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id, 
            timestamp, 
            content, 
            role, 
            conversation_id,
            json.dumps(metadata) if metadata else None
        ))
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return message_id, conversation_id
    
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
        
        cursor.execute("""
        SELECT id, user_id, timestamp, content, role, metadata
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
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
            "metadata": json.loads(row[5]) if row[5] else None
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