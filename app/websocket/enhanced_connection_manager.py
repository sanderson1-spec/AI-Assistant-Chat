"""
Enhanced WebSocket connection manager supporting user tracking and notifications
"""
from typing import Dict, List, Any, Optional
import logging
from fastapi import WebSocket, WebSocketDisconnect

class EnhancedConnectionManager:
    """
    Connection manager for WebSockets with user tracking and notifications
    """
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}  # Maps user_id to list of client_ids
        self.logger = logging.getLogger("ai-assistant.websocket-manager")
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Connect a WebSocket client
        
        Args:
            websocket: The WebSocket connection
            client_id: Unique client identifier
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.logger.info(f"Client {client_id} connected")
    
    def add_user_connection(self, client_id: str, user_id: str = "default_user"):
        """
        Associate a client connection with a user ID (without accepting the websocket again)
        
        Args:
            client_id: Unique client identifier
            user_id: ID of the user associated with this connection
        """
        # Associate this client with the user
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        if client_id not in self.user_connections[user_id]:
            self.user_connections[user_id].append(client_id)
        
        self.logger.info(f"Associated client {client_id} with user {user_id}")
    
    def disconnect(self, client_id: str):
        """
        Disconnect a WebSocket client
        
        Args:
            client_id: Unique client identifier
        """
        if client_id in self.active_connections:
            # Remove from user associations
            for user_id, clients in list(self.user_connections.items()):
                if client_id in clients:
                    self.user_connections[user_id].remove(client_id)
                    # Clean up empty user entries
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
                    break
            
            # Remove from active connections
            del self.active_connections[client_id]
            self.logger.info(f"Client {client_id} disconnected")
    
    async def send_message(self, client_id: str, message: dict):
        """
        Send a message to a specific client
        
        Args:
            client_id: Unique client identifier
            message: Message data to send (will be JSON-encoded)
        """
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                self.logger.error(f"Error sending message to client {client_id}: {str(e)}")
                # Connection probably broken, disconnect
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients
        
        Args:
            message: Message data to broadcast (will be JSON-encoded)
        """
        for client_id in list(self.active_connections.keys()):
            await self.send_message(client_id, message)
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """
        Broadcast a message to all connections for a specific user
        
        Args:
            user_id: ID of the user to send to
            message: Message data to broadcast (will be JSON-encoded)
        """
        for client_id in self.get_client_ids_for_user(user_id):
            await self.send_message(client_id, message)
    
    def get_client_ids_for_user(self, user_id: str) -> List[str]:
        """
        Get all client IDs associated with a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of client IDs
        """
        return self.user_connections.get(user_id, [])
    
    def is_user_connected(self, user_id: str) -> bool:
        """
        Check if a user has any active connections
        
        Args:
            user_id: ID of the user
            
        Returns:
            True if connected, False otherwise
        """
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0