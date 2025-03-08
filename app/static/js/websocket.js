/**
 * WebSocket connection handling
 */
import MessageHandler from './message-handlers.js';
import ConversationManager from './conversation-manager.js';

const WebSocketManager = {
    socket: null,
    clientId: null,
    userId: 'default_user',
    
    /**
     * Initialize WebSocket connection
     * @param {string} userId - The user ID
     */
    init: function(userId) {
        this.userId = userId || 'default_user';
        this.clientId = this.generateClientId();
        this.connectWebSocket();
    },
    
    /**
     * Generate a unique client ID
     * @returns {string} A unique client identifier
     */
    generateClientId: function() {
        return Math.random().toString(36).substring(2, 15) + 
               Date.now().toString(36);
    },
    
    /**
     * Connect to the WebSocket server with more robust error handling
     */
    connectWebSocket: function() {
        // Determine WebSocket protocol based on current page
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        
        // Construct WebSocket URL with explicit host and port
        const wsUrl = `${protocol}//${window.location.hostname}:${window.location.port}/ws/${this.clientId}`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected successfully');
            // Optionally send a connect message
            this.sendMessage({
                type: 'connect',
                user_id: this.userId,
                client_id: this.clientId
            });
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket message received:', data);
                
                // Handle different message types
                switch(data.type) {
                    case 'message':
                        MessageHandler.handleIncomingMessage(data);
                        break;
                    case 'notification':
                        console.log('Notification received:', data);
                        // Ensure NotificationHandler is available globally
                        if (window.NotificationHandler) {
                            window.NotificationHandler.handleNotification(data);
                        } else {
                            console.error('NotificationHandler not available');
                            // Try to import it dynamically if not available
                            import('./notification-handler.js').then(module => {
                                window.NotificationHandler = module.default;
                                window.NotificationHandler.init();
                                window.NotificationHandler.handleNotification(data);
                            }).catch(error => {
                                console.error('Failed to load NotificationHandler:', error);
                            });
                        }
                        break;
                    case 'error':
                        console.error('Server WebSocket error:', data.message);
                        MessageHandler.displaySystemMessage(data.message || 'An error occurred');
                        break;
                    default:
                        console.log('Unhandled WebSocket message type:', data.type);
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.socket.onclose = (event) => {
            console.log('WebSocket disconnected:', event);
            
            // Attempt to reconnect with exponential backoff
            this.scheduleReconnect();
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            MessageHandler.displaySystemMessage('Connection error. Attempting to reconnect...');
        };
    },
    
    /**
     * Schedule a reconnection attempt with exponential backoff
     */
    scheduleReconnect: function() {
        // If we don't have a reconnect attempt count, start at 1
        this.reconnectAttempts = (this.reconnectAttempts || 0) + 1;
        
        // Calculate exponential backoff (max 30 seconds)
        const delay = Math.min(
            Math.pow(2, this.reconnectAttempts) * 1000, 
            30000
        );
        
        console.log(`Attempting to reconnect in ${delay/1000} seconds`);
        
        setTimeout(() => {
            console.log('Attempting WebSocket reconnection');
            this.connectWebSocket();
        }, delay);
    },
    
    /**
     * Send a message through the WebSocket
     * @param {Object} messageData - The message data to send
     */
    sendMessage: function(messageData) {
        // Ensure we have a conversation ID
        if (!messageData.conversation_id && messageData.type === 'message') {
            messageData.conversation_id = ConversationManager.getCurrentConversationId();
        }
        
        // Ensure we have a user ID
        if (!messageData.user_id) {
            messageData.user_id = this.userId;
        }
        
        // Default to a 'message' type if not specified
        if (!messageData.type) {
            messageData.type = 'message';
        }
        
        // Add client ID for tracking
        messageData.client_id = this.clientId;
        
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            try {
                console.log('Sending WebSocket message:', JSON.stringify(messageData).slice(0, 200) + '...');
                this.socket.send(JSON.stringify(messageData));
            } catch (error) {
                console.error('Error sending WebSocket message:', error);
                MessageHandler.displaySystemMessage('Failed to send message. Please try again.');
            }
        } else {
            console.error('WebSocket not connected');
            MessageHandler.displaySystemMessage('Connection lost. Attempting to reconnect...');
            
            // Attempt to reconnect
            this.connectWebSocket();
        }
    },
    
    /**
     * Check if the WebSocket is connected
     * @returns {boolean} True if connected, false otherwise
     */
    isConnected: function() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    },
    
    /**
     * Get user ID associated with this connection
     * @returns {string} The user ID
     */
    getUserId: function() {
        return this.userId;
    }
};

export default WebSocketManager;