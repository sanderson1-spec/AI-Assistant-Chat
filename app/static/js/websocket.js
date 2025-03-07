/**
 * WebSocket connection handling
 */
import MessageHandler from './message-handlers.js';

const WebSocketManager = {
    socket: null,
    clientId: null,
    
    /**
     * Initialize WebSocket connection
     * @param {string} userId - The user ID
     */
    init: function(userId) {
        this.clientId = Math.random().toString(36).substring(2, 15);
        this.connectWebSocket(userId);
    },
    
    /**
     * Connect to the WebSocket server
     * @param {string} userId - The user ID
     */
    connectWebSocket: function(userId) {
        this.socket = new WebSocket(`ws://${window.location.host}/ws/${this.clientId}`);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                MessageHandler.handleIncomingMessage(data);
            }
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            // Try to reconnect after a delay
            setTimeout(() => this.connectWebSocket(userId), 3000);
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    },
    
    /**
     * Send a message through the WebSocket
     * @param {Object} messageData - The message data to send
     */
    sendMessage: function(messageData) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(messageData));
        } else {
            console.error('WebSocket not connected');
            // Use a direct DOM manipulation here since we might have circular reference issues
            const chatContainer = document.getElementById('chat-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message system-message';
            messageDiv.textContent = 'Error: Cannot connect to server';
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    },
    
    /**
     * Check if the WebSocket is connected
     * @returns {boolean} True if connected, false otherwise
     */
    isConnected: function() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    }
};

export default WebSocketManager;