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

/**
 * Send message to the server
 */
function sendMessage() {
    console.log('Send button clicked');
    const messageText = UIController.getMessageInput();
    
    if (!messageText) return;
    
    // Prepare message data
    const messageData = {
        type: 'message',
        user_id: config.userId,
        message: messageText,
        conversation_id: ConversationManager.getCurrentConversationId()
    };
    
    try {
        // Use MessageHandler to process and display the user message
        const userMessageData = MessageHandler.sendUserMessage(
            messageText, 
            config.userId, 
            ConversationManager.getCurrentConversationId()
        );
        
        // Clear input field
        UIController.clearMessageInput();
        
        // Send to server via WebSocket
        WebSocketManager.sendMessage(messageData);
    } catch (error) {
        console.error('Error sending message:', error);
        MessageHandler.displaySystemMessage('Failed to send message. Please try again.');
    }
}

/**
 * Handle keyboard shortcuts
 * @param {KeyboardEvent} event - Keyboard event
 */
function handleGlobalKeyboard(event) {
    // Cmd+Enter to send message
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
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
    
    // Set up UI
    UIController.setupTextareaInput();
    UIController.addKeyboardShortcutInfo();
    
    // Set up direct event listeners for critical functionality
    const sendButton = document.getElementById('send-button');
    const messageInput = document.getElementById('message-input');
    const newChatButton = document.getElementById('new-chat-button');
    
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    } else {
        console.error('Send button not found');
    }
    
    if (messageInput) {
        // Ensure Enter sends message unless Shift is pressed
        messageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });
    } else {
        console.error('Message input not found');
    }
    
    if (newChatButton) {
        newChatButton.addEventListener('click', () => {
            ConversationManager.newConversation();
        });
    } else {
        console.error('New chat button not found');
    }
    
    // Add global keyboard shortcut listener
    document.addEventListener('keydown', handleGlobalKeyboard);
    
    console.log('AI Assistant initialized');
}

// Initialize the app when DOM is fully loaded
document.addEventListener('DOMContentLoaded', initApp);

// Export public API for potential external use
export default {
    init: initApp,
    sendMessage: sendMessage
};