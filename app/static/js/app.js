/**
 * Main entry point for the AI Assistant application
 */
import WebSocketManager from './websocket.js';
import ConversationManager from './conversation-manager.js';
import MessageHandler from './message-handlers.js';
import UIController from './ui-controller.js';

// Application configuration
const config = {
    userId: 'default_user'
};

// Define send message function
function sendMessage() {
    console.log('Send button clicked');
    const messageText = UIController.getMessageInput();
    if (!messageText) return;
    
    const messageData = MessageHandler.sendUserMessage(
        messageText, 
        config.userId, 
        ConversationManager.getCurrentConversationId()
    );
    
    if (messageData) {
        // Clear input field
        UIController.clearMessageInput();
        
        // Send to server via WebSocket
        WebSocketManager.sendMessage(messageData);
    }
}

/**
 * Initialize the application
 */
function initApp() {
    console.log('Initializing AI Assistant...');
    
    // Initialize components
    WebSocketManager.init(config.userId);
    ConversationManager.init(config.userId);
    
    // Set up direct event listeners for critical functionality
    document.getElementById('send-button').addEventListener('click', sendMessage);
    
    document.getElementById('message-input').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
    
    document.getElementById('new-chat-button').addEventListener('click', () => {
        ConversationManager.newConversation();
    });
    
    console.log('AI Assistant initialized');
}

// Initialize the app when DOM is fully loaded
document.addEventListener('DOMContentLoaded', initApp);

// Export public API for potential external use
export default {
    init: initApp,
    sendMessage: sendMessage
};