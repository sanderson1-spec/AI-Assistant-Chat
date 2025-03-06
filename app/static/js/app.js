/**
 * app.js - Main entry point for the chat application
 */

// Global application configuration
window.appConfig = {
    userId: 'default_user',
    clientId: Math.random().toString(36).substring(2, 15)
};

/**
 * Handle sending a message when the send button is clicked or Enter is pressed
 */
function handleSendMessage() {
    const messageInput = window.chatUtils.getElement('message-input');
    if (!messageInput) return;
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Send the message and clear input if successful
    if (window.messageHandlers.sendUserMessage(message)) {
        messageInput.value = '';
    }
}

/**
 * Register WebSocket message callbacks
 */
function registerWebSocketCallbacks() {
    window.wsClient.registerCallbacks({
        onUserMessage: (data) => {
            window.messageHandlers.addMessage(data.content, 'user');
        },
        
        onAssistantMessage: (data) => {
            // If this is a response to a user message
            if (data.response_to_id) {
                window.conversationManager.addResponseVersion(data.response_to_id, data.content);
            } else {
                window.messageHandlers.addMessage(data.content, 'assistant');
            }
            
            // Update conversation ID if provided
            if (data.conversation_id) {
                // Reload conversations list to show the new conversation
                window.conversationManager.loadConversationsList();
            }
        },
        
        onSystemMessage: (data) => {
            window.messageHandlers.addMessage(data.content, 'system');
        },
        
        onConnectionChange: (isConnected) => {
            // Update UI to show connection status if needed
            const sendButton = window.chatUtils.getElement('send-button');
            if (sendButton) {
                sendButton.disabled = !isConnected;
                sendButton.style.opacity = isConnected ? '1' : '0.5';
            }
        }
    });
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Send button click
    const sendButton = window.chatUtils.getElement('send-button');
    if (sendButton) {
        sendButton.addEventListener('click', handleSendMessage);
    }
    
    // Message input Enter key
    const messageInput = window.chatUtils.getElement('message-input');
    if (messageInput) {
        messageInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleSendMessage();
            }
        });
    }
    
    // New chat button
    const newChatButton = window.chatUtils.getElement('new-chat-button');
    if (newChatButton) {
        newChatButton.addEventListener('click', window.conversationManager.startNewConversation);
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Command+R (Mac) or Ctrl+R (Windows/Linux) for regenerating response
        if ((event.metaKey || event.ctrlKey) && event.key === 'r') {
            event.preventDefault(); // Prevent browser refresh
            
            // Find the last message and its user message
            const messages = window.messageHandlers.getAllMessages();
            for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].role === 'assistant' && messages[i].responseToId) {
                    window.conversationManager.regenerateResponse(messages[i].responseToId);
                    break;
                }
            }
        }
    });
}

/**
 * Initialize the application
 */
function initializeApp() {
    try {
        // Connect to WebSocket
        window.wsClient.connect(window.appConfig.clientId);
        
        // Register WebSocket callbacks
        registerWebSocketCallbacks();
        
        // Set up event listeners
        setupEventListeners();
        
        // Load conversations list
        window.conversationManager.loadConversationsList();
        
        window.chatUtils.showDebugMessage('Chat application initialized successfully');
    } catch (error) {
        console.error('Error initializing application:', error);
        window.chatUtils.showDebugMessage(`Error initializing application: ${error.message}`, true);
    }
}

// Initialize when the DOM is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}