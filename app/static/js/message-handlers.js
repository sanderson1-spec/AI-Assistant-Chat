/**
 * Message creation and handling
 */
import MessageFormatter from './message-formatter.js';
import UIController from './ui-controller.js';
import ConversationManager from './conversation-manager.js';

const MessageHandler = {
    /**
     * Process and display a new user message
     * @param {string} messageText - The message text
     * @param {string} userId - The user ID
     * @param {string|null} conversationId - The conversation ID, if any
     * @returns {Object} Message data object
     */
    sendUserMessage: function(messageText, userId, conversationId) {
        if (!messageText.trim()) return false;
        
        // Display the message in the UI
        this.displayMessage(messageText, 'user');
        
        // Prepare the message data
        const messageData = {
            user_id: userId,
            message: messageText,
            conversation_id: conversationId
        };
        
        return messageData;
    },
    
    /**
     * Handle incoming message from the server
     * @param {Object} data - The message data
     */
    handleIncomingMessage: function(data) {
        this.displayMessage(data.content, data.role);
        
        if (data.conversation_id) {
            ConversationManager.setCurrentConversationId(data.conversation_id);
            ConversationManager.loadConversations();
        }
    },
    
    /**
     * Display a message in the chat UI
     * @param {string} content - The message content
     * @param {string} role - The role (user/assistant)
     */
    displayMessage: function(content, role) {
        const messageElement = MessageFormatter.formatMessage(content, role);
        UIController.addMessageToChat(messageElement);
    },
    
    /**
     * Display a system message in the chat
     * @param {string} message - The system message
     */
    displaySystemMessage: function(message) {
        this.displayMessage(message, 'system');
    }
};

export default MessageHandler;