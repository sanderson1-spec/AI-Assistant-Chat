/**
 * conversation-manager.js - Manages conversations and responses
 */

// Module variables
let currentConversationId = null;
let responseVersions = {};

/**
 * Load a specific conversation
 * @param {string} conversationId - ID of the conversation to load
 */
async function loadConversation(conversationId) {
    try {
        currentConversationId = conversationId;
        const response = await fetch(`/api/conversations/${conversationId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const chatContainer = window.chatUtils.getElement('chat-container');
        if (!chatContainer) {
            return;
        }
        
        // Clear existing chat and history
        chatContainer.innerHTML = '';
        window.messageHandlers.clearMessages();
        responseVersions = {};
        
        // Process messages first to build response versions
        data.messages.forEach(message => {
            if (message.role === 'assistant' && message.metadata && message.metadata.responseToId) {
                const userMsgId = message.metadata.responseToId;
                if (!responseVersions[userMsgId]) {
                    responseVersions[userMsgId] = [];
                }
                responseVersions[userMsgId].push({
                    content: message.content,
                    timestamp: message.timestamp,
                    messageId: message.message_id || message.id
                });
            }
        });
        
        // Display messages
        data.messages.forEach(message => {
            // Skip assistant messages that are responses (they'll be handled separately)
            if (message.role === 'assistant' && message.metadata && message.metadata.responseToId) {
                return;
            }
            
            // Add the message
            const messageId = window.messageHandlers.addMessage(
                message.content, 
                message.role,
                message.message_id || message.id
            );
            
            // If it's a user message, check if it has responses
            if (message.role === 'user') {
                const userMsgId = message.message_id || message.id;
                const versions = responseVersions[userMsgId];
                
                if (versions && versions.length > 0) {
                    // Show the latest version
                    const latestVersion = versions[versions.length - 1];
                    addAssistantResponse(latestVersion.content, userMsgId, versions.length - 1, versions.length);
                }
            }
        });
    } catch (error) {
        window.chatUtils.showDebugMessage(`Error loading conversation: ${error.message}`, true);
        console.error('Error loading conversation:', error);
    }
}

/**
 * Add an assistant response to a user message
 * @param {string} content - Response content
 * @param {string} userMessageId - ID of the user message
 * @param {number} versionIndex - Index of this version
 * @param {number} totalVersions - Total number of versions
 */
function addAssistantResponse(content, userMessageId, versionIndex, totalVersions) {
    const chatContainer = window.chatUtils.getElement('chat-container');
    if (!chatContainer) return;
    
    const messageId = window.chatUtils.generateId();
    
    // Find the user message container
    const userMsgContainer = document.querySelector(`.message-container[data-message-id="${userMessageId}"]`);
    let assistantMsgContainer;
    
    if (userMsgContainer && userMsgContainer.nextElementSibling && 
        userMsgContainer.nextElementSibling.querySelector('.assistant-message')) {
        // Response exists, update it
        assistantMsgContainer = userMsgContainer.nextElementSibling;
        const messageDiv = assistantMsgContainer.querySelector('.message');
        messageDiv.innerHTML = window.messageFormatter.formatMarkdown(content);
        messageDiv.dataset.rawContent = content;
        messageDiv.dataset.versionIndex = versionIndex.toString();
        
        // Update timestamp
        const timestampDiv = messageDiv.querySelector('.message-timestamp');
        if (timestampDiv) {
            timestampDiv.textContent = window.messageFormatter.formatTimestamp(new Date());
        }
        
        // Update versions UI
        window.uiController.updateVersionsUI(assistantMsgContainer, userMessageId, versionIndex, totalVersions);
    } else {
        // Create new response
        assistantMsgContainer = document.createElement('div');
        assistantMsgContainer.className = 'message-container';
        assistantMsgContainer.dataset.responseToMessageId = userMessageId;
        
        // Create message div
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        messageDiv.innerHTML = window.messageFormatter.formatMarkdown(content);
        messageDiv.dataset.rawContent = content;
        messageDiv.dataset.versionIndex = versionIndex.toString();
        
        // Add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        timestampDiv.textContent = window.messageFormatter.formatTimestamp(new Date());
        messageDiv.appendChild(timestampDiv);
        
        // Create regenerate button
        const regenerateBtn = window.uiController.createRegenerateButton(userMessageId);
        
        // Create versions container and add version buttons if needed
        const versionsContainer = window.uiController.createVersionControls(
            userMessageId, 
            versionIndex, 
            totalVersions
        );
        
        // Assemble the components
        assistantMsgContainer.appendChild(messageDiv);
        assistantMsgContainer.appendChild(regenerateBtn);
        assistantMsgContainer.appendChild(versionsContainer);
        
        // Insert after user message
        if (userMsgContainer && userMsgContainer.nextSibling) {
            chatContainer.insertBefore(assistantMsgContainer, userMsgContainer.nextSibling);
        } else if (userMsgContainer) {
            chatContainer.appendChild(assistantMsgContainer);
        }
    }
    
    // Scroll to bottom
    window.uiController.scrollToBottom();
}

/**
 * Load conversations list
 */
async function loadConversationsList() {
    try {
        const response = await fetch(`/api/conversations?user_id=${window.appConfig.userId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        const conversationsList = window.chatUtils.getElement('conversations-list');
        if (!conversationsList) {
            return;
        }
        
        conversationsList.innerHTML = '';
        
        data.conversations.forEach(conv => {
            const convItem = window.uiController.createConversationItem(
                conv,
                loadConversation,
                deleteConversation
            );
            conversationsList.appendChild(convItem);
        });
        
        // Add a "Clear All" button if there are conversations
        if (data.conversations.length > 0) {
            const clearAllButton = document.createElement('button');
            clearAllButton.textContent = 'Clear All Conversations';
            clearAllButton.className = 'clear-all-button';
            clearAllButton.onclick = clearAllConversations;
            conversationsList.appendChild(document.createElement('hr'));
            conversationsList.appendChild(clearAllButton);
        }
    } catch (error) {
        window.chatUtils.showDebugMessage(`Error loading conversations: ${error.message}`, true);
        console.error('Error loading conversations:', error);
    }
}

/**
 * Delete a conversation
 * @param {string} conversationId - ID of the conversation to delete
 */
async function deleteConversation(conversationId) {
    if (!confirm("Are you sure you want to delete this conversation?")) {
        return;
    }
    
    try {
        const response = await fetch(`/api/conversations/${conversationId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ user_id: window.appConfig.userId })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // If the deleted conversation was the current one, clear the chat
        if (currentConversationId === conversationId) {
            currentConversationId = null;
            const chatContainer = window.chatUtils.getElement('chat-container');
            if (chatContainer) {
                chatContainer.innerHTML = '';
            }
            window.messageHandlers.clearMessages();
            responseVersions = {};
        }
        
        // Reload the conversations list
        loadConversationsList();
    } catch (error) {
        window.chatUtils.showDebugMessage(`Error deleting conversation: ${error.message}`, true);
        console.error('Error deleting conversation:', error);
    }
}

/**
 * Clear all conversations
 */
async function clearAllConversations() {
    if (!confirm("Are you sure you want to delete ALL conversations? This cannot be undone.")) {
        return;
    }
    
    try {
        const response = await fetch(`/api/conversations?user_id=${window.appConfig.userId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Clear current chat
        currentConversationId = null;
        const chatContainer = window.chatUtils.getElement('chat-container');
        if (chatContainer) {
            chatContainer.innerHTML = '';
        }
        window.messageHandlers.clearMessages();
        responseVersions = {};
        
        // Reload conversations list (should be empty)
        loadConversationsList();
    } catch (error) {
        window.chatUtils.showDebugMessage(`Error clearing conversations: ${error.message}`, true);
        console.error('Error clearing conversations:', error);
    }
}

/**
 * Start a new conversation
 */
function startNewConversation() {
    currentConversationId = null;
    const chatContainer = window.chatUtils.getElement('chat-container');
    if (chatContainer) {
        chatContainer.innerHTML = '';
    }
    window.messageHandlers.clearMessages();
    responseVersions = {};
}

/**
 * Get the current conversation ID
 * @returns {string|null} - Current conversation ID or null if no conversation is active
 */
function getCurrentConversationId() {
    return currentConversationId;
}

/**
 * Add a new version of a response
 * @param {string} userMessageId - ID of the user message
 * @param {string} content - Response content
 */
function addResponseVersion(userMessageId, content) {
    if (!responseVersions[userMessageId]) {
        responseVersions[userMessageId] = [];
    }
    
    responseVersions[userMessageId].push({
        content: content,
        timestamp: new Date().toISOString()
    });
    
    const versionIndex = responseVersions[userMessageId].length - 1;
    addAssistantResponse(
        content, 
        userMessageId, 
        versionIndex, 
        responseVersions[userMessageId].length
    );
}

/**
 * Switch to a different version of a response
 * @param {string} userMessageId - ID of the user message
 * @param {number} versionIndex - Index of the version to switch to
 */
function switchResponseVersion(userMessageId, versionIndex) {
    const versions = responseVersions[userMessageId];
    if (!versions || versionIndex >= versions.length) return;
    
    const assistantMsgContainer = document.querySelector(`.message-container[data-response-to-message-id="${userMessageId}"]`);
    if (!assistantMsgContainer) return;
    
    const messageDiv = assistantMsgContainer.querySelector('.message');
    if (!messageDiv) return;
    
    messageDiv.innerHTML = window.messageFormatter.formatMarkdown(versions[versionIndex].content);
    messageDiv.dataset.rawContent = versions[versionIndex].content;
    messageDiv.dataset.versionIndex = versionIndex.toString();
    
    // Update version buttons
    window.uiController.updateVersionsUI(
        assistantMsgContainer, 
        userMessageId, 
        versionIndex, 
        versions.length
    );
}

/**
 * Regenerate a response to a user message
 * @param {string} userMessageId - ID of the user message
 */
function regenerateResponse(userMessageId) {
    // Find the user message
    const userMsgElement = document.querySelector(`.message-container[data-message-id="${userMessageId}"] .message`);
    if (!userMsgElement) return;
    
    const content = userMsgElement.dataset.rawContent;
    if (!content) return;
    
    // Send the message again to get a new response
    if (window.wsClient.isConnected()) {
        window.wsClient.send({
            user_id: window.appConfig.userId,
            message: content,
            conversation_id: currentConversationId,
            regenerate: true,
            message_id: userMessageId
        });
    } else {
        window.chatUtils.showDebugMessage('WebSocket not connected. Cannot regenerate response.', true);
    }
}

// Export conversation manager functions
window.conversationManager = {
    loadConversation,
    loadConversationsList,
    deleteConversation,
    clearAllConversations,
    startNewConversation,
    getCurrentConversationId,
    addResponseVersion,
    switchResponseVersion,
    regenerateResponse
};