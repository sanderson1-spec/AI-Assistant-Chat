"""
Vector database for storing and retrieving conversations and memories
Using ChromaDB for efficient semantic search
"""
import chromadb
from chromadb.config import Settings
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

class VectorStore:
    """Manages vector storage for conversations and memories"""
    
    def __init__(self, data_dir: str = "data/vector_db"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("ai-assistant.vector-store")
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.data_dir))
        
        # Initialize sentence transformer for embeddings
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create collections if they don't exist
        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            metadata={"description": "Stores conversation history"}
        )
        
        self.memories = self.client.get_or_create_collection(
            name="memories",
            metadata={"description": "Stores character memories"}
        )
        
        self.logger.info("Vector store initialized")
    
    async def store_conversation(
        self, 
        conversation_id: str,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store a conversation in the vector database
        
        Args:
            conversation_id: Unique conversation identifier
            messages: List of message dictionaries
            metadata: Additional metadata about the conversation
        """
        # Combine messages into a single document for embedding
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in messages
        )
        
        # Generate embedding
        embedding = self.encoder.encode(conversation_text).tolist()
        
        # Prepare metadata
        meta = {
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            **(metadata or {})
        }
        
        # Store in ChromaDB
        self.conversations.upsert(
            ids=[conversation_id],
            embeddings=[embedding],
            documents=[conversation_text],
            metadatas=[meta]
        )
        
        self.logger.info(f"Stored conversation {conversation_id}")
    
    async def store_memory(
        self,
        character_id: str,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store a memory in the vector database
        
        Args:
            character_id: ID of the character this memory belongs to
            memory_id: Unique memory identifier
            content: Memory content text
            metadata: Additional metadata about the memory
        """
        # Generate embedding
        embedding = self.encoder.encode(content).tolist()
        
        # Prepare metadata
        meta = {
            "character_id": character_id,
            "memory_id": memory_id,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        # Store in ChromaDB
        self.memories.upsert(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta]
        )
        
        self.logger.info(f"Stored memory {memory_id} for character {character_id}")
    
    async def find_similar_memories(
        self,
        query: str,
        character_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find memories similar to the query text
        
        Args:
            query: Text to find similar memories for
            character_id: ID of the character whose memories to search
            limit: Maximum number of memories to return
            
        Returns:
            List of similar memories with their metadata
        """
        # Generate query embedding
        query_embedding = self.encoder.encode(query).tolist()
        
        # Search in ChromaDB
        results = self.memories.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"character_id": character_id}
        )
        
        # Format results
        memories = []
        for i, (doc, meta, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            memories.append({
                "content": doc,
                "metadata": meta,
                "relevance_score": 1 - distance  # Convert distance to similarity score
            })
        
        return memories
    
    async def find_similar_conversations(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find conversations similar to the query text
        
        Args:
            query: Text to find similar conversations for
            limit: Maximum number of conversations to return
            metadata_filter: Filter results by metadata fields
            
        Returns:
            List of similar conversations with their metadata
        """
        # Generate query embedding
        query_embedding = self.encoder.encode(query).tolist()
        
        # Search in ChromaDB
        results = self.conversations.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=metadata_filter
        )
        
        # Format results
        conversations = []
        for i, (doc, meta, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            conversations.append({
                "content": doc,
                "metadata": meta,
                "relevance_score": 1 - distance
            })
        
        return conversations
    
    async def get_conversation_history(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a specific conversation by ID"""
        results = self.conversations.get(
            ids=[conversation_id],
            include=["documents", "metadatas"]
        )
        
        if results["ids"]:
            return {
                "content": results["documents"][0],
                "metadata": results["metadatas"][0]
            }
        return None
    
    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation from the database"""
        self.conversations.delete(ids=[conversation_id])
        self.logger.info(f"Deleted conversation {conversation_id}")
    
    async def delete_memory(self, memory_id: str):
        """Delete a memory from the database"""
        self.memories.delete(ids=[memory_id])
        self.logger.info(f"Deleted memory {memory_id}")
    
    async def consolidate_memories(self, character_id: str):
        """
        Consolidate memories for a character by finding patterns
        and creating higher-level memories
        """
        # Get all memories for the character
        results = self.memories.get(
            where={"character_id": character_id}
        )
        
        if not results["ids"]:
            return
        
        # Group memories by their embeddings using clustering
        embeddings = np.array(results["embeddings"])
        # TODO: Implement memory clustering and consolidation
        # This would involve:
        # 1. Clustering similar memories
        # 2. Generating summaries for each cluster
        # 3. Creating new consolidated memories
        # 4. Updating importance scores
        pass 