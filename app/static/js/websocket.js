/**
 * websocket.js - Handles WebSocket connection and message sending
 */

// Module variables
let socket = null;
let messageCallbacks = {
    onUserMessage: null,
    onAssistantMessage: null,
    onSystemMessage: null,
    onConnectionChange: null
};

/**
 * Connect to the WebSocket server
 * @param {string} clientId - Unique client identifier
 */
function connectWebSocket(clientId) {
    try {
        const wsUrl = `ws://${window.location.host}/ws/${clientId}`;
        window.chatUtils.showDebugMessage(`Attempting to connect to WebSocket at ${wsUrl}`);
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            window.chatUtils.showDebugMessage('WebSocket connected successfully');
            if (messageCallbacks.onConnectionChange) {
                messageCallbacks.onConnectionChange(true);
            }
        };
        
        socket.onmessage = (event) => {
            try {
                const data = window.chatUtils.safeJsonParse(event.data);
                if (!data) return;
                
                if (data.type === 'message') {
                    if (data.role === 'assistant' && messageCallbacks.onAssistantMessage) {
                        messageCallbacks.onAssistantMessage(data);
                    } else if (data.role === 'user' && messageCallbacks.onUserMessage) {
                        messageCallbacks.onUserMessage(data);
                    } else if (data.role === 'system' && messageCallbacks.onSystemMessage) {
                        messageCallbacks.onSystemMessage(data);
                    }
                }
            } catch (error) {
                window.chatUtils.showDebugMessage(`Error parsing WebSocket message: ${error.message}`, true);
                console.error('WebSocket message error:', error);
            }
        };
        
        socket.onclose = (event) => {
            window.chatUtils.showDebugMessage(`WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason || 'No reason provided'}`, true);
            if (messageCallbacks.onConnectionChange) {
                messageCallbacks.onConnectionChange(false);
            }
            // Try to reconnect after a delay
            setTimeout(() => connectWebSocket(clientId), 3000);
        };
        
        socket.onerror = (error) => {
            window.chatUtils.showDebugMessage(`WebSocket error occurred`, true);
            console.error('WebSocket error:', error);
        };
    } catch (error) {
        window.chatUtils.showDebugMessage(`Exception during WebSocket connection: ${error.message}`, true);
        console.error('WebSocket connection error:', error);
    }
}

/**
 * Send a message through the WebSocket
 * @param {object} payload - Message payload to send
 * @returns {boolean} - Whether the message was sent successfully
 */
function sendMessage(payload) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        try {
            socket.send(JSON.stringify(payload));
            return true;
        } catch (error) {
            window.chatUtils.showDebugMessage(`Error sending message: ${error.message}`, true);
            return false;
        }
    } else {
        window.chatUtils.showDebugMessage(`WebSocket not connected. Current state: ${socket ? socket.readyState : 'No socket'}`, true);
        return false;
    }
}

/**
 * Register message handling callbacks
 * @param {object} callbacks - Object containing callback functions
 */
function registerCallbacks(callbacks) {
    messageCallbacks = {
        ...messageCallbacks,
        ...callbacks
    };
}

/**
 * Check if WebSocket is connected
 * @returns {boolean} - Whether the WebSocket is currently connected
 */
function isConnected() {
    return socket && socket.readyState === WebSocket.OPEN;
}

// Export WebSocket functions for use in other modules
window.wsClient = {
    connect: connectWebSocket,
    send: sendMessage,
    registerCallbacks,
    isConnected
};