/**
 * Manage conversations in the chat application
 */
import UIController from './ui-controller.js';
import MessageHandler from './message-handlers.js';

const ConversationManager = {
    currentConversationId: null,
    userId: 'default_user',
    
    /**
     * Initialize conversation manager
     * @param {string} userId - The user ID
     */
    init: function(userId) {
        this.userId = userId || 'default_user';
        this.loadConversations();
    },
    
    /**
     * Set the current conversation ID
     * @param {string} conversationId - The conversation ID
     */
    setCurrentConversationId: function(conversationId) {
        this.currentConversationId = conversationId;
    },
    
    /**
     * Get the current conversation ID
     * @returns {string|null} The current conversation ID
     */
    getCurrentConversationId: function() {
        return this.currentConversationId;
    },
    
    /**
     * Start a new conversation
     */
    newConversation: function() {
        this.currentConversationId = null;
        UIController.clearChatMessages();
    },
    
    /**
     * Load conversation list from the server
     */
    loadConversations: async function() {
        try {
            const response = await fetch(`/api/conversations?user_id=${this.userId}`);
            const data = await response.json();
            
            UIController.displayConversationList(
                data.conversations,
                this.loadConversation.bind(this),
                this.deleteConversation.bind(this),
                this.clearAllConversations.bind(this)
            );
        } catch (error) {
            console.error('Error loading conversations:', error);
        }
    },
    
    /**
     * Load a specific conversation
     * @param {string} conversationId - The conversation ID
     */
    loadConversation: async function(conversationId) {
        try {
            this.currentConversationId = conversationId;
            const response = await fetch(`/api/conversations/${conversationId}`);
            const data = await response.json();
            
            UIController.clearChatMessages();
            
            data.messages.forEach(message => {
                MessageHandler.displayMessage(message.content, message.role);
            });
        } catch (error) {
            console.error('Error loading conversation:', error);
        }
    },
    
    /**
     * Delete a conversation
     * @param {string} conversationId - The conversation ID
     */
    deleteConversation: async function(conversationId) {
        if (!confirm("Are you sure you want to delete this conversation?")) {
            return;
        }
        
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            if (response.ok) {
                // If the deleted conversation was the current one, clear the chat
                if (this.currentConversationId === conversationId) {
                    this.currentConversationId = null;
                    UIController.clearChatMessages();
                }
                
                // Reload the conversations list
                this.loadConversations();
            } else {
                console.error('Failed to delete conversation');
            }
        } catch (error) {
            console.error('Error deleting conversation:', error);
        }
    },
    
    /**
     * Clear all conversations
     */
    clearAllConversations: async function() {
        if (!confirm("Are you sure you want to delete ALL conversations? This cannot be undone.")) {
            return;
        }
        
        try {
            const response = await fetch(`/api/conversations?user_id=${this.userId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // Clear current chat
                this.currentConversationId = null;
                UIController.clearChatMessages();
                
                // Reload conversations list (should be empty)
                this.loadConversations();
            } else {
                console.error('Failed to clear conversations');
            }
        } catch (error) {
            console.error('Error clearing conversations:', error);
        }
    }
};

export default ConversationManager;