/**
 * message-handlers.js - Handles message creation, editing, and deletion
 */

// Module variables
let messageHistory = [];

/**
 * Add a message to the chat history and UI
 * @param {string} content - Message content
 * @param {string} role - Message role (user, assistant, system)
 * @param {string} [customId] - Optional custom message ID
 * @returns {string} - ID of the added message
 */
function addMessage(content, role, customId = null) {
    const messageId = customId || window.chatUtils.generateId();
    const chatContainer = window.chatUtils.getElement('chat-container');
    if (!chatContainer) return messageId;
    
    // Add to message history
    messageHistory.push({
        id: messageId,
        content: content,
        role: role,
        timestamp: new Date().toISOString()
    });
    
    // Create and add message element
    const messageElement = window.uiController.createMessageElement(content, role, messageId);
    chatContainer.appendChild(messageElement);
    
    // Add regenerate button for assistant messages that follow a user message
    if (role === 'assistant' && messageHistory.length > 1) {
        // Find the preceding user message
        const prevMsg = messageHistory[messageHistory.length - 2];
        if (prevMsg && prevMsg.role === 'user') {
            const regenerateBtn = window.uiController.createRegenerateButton(prevMsg.id);
            messageElement.appendChild(regenerateBtn);
            
            // Create empty versions container (will be populated as needed)
            const versionsContainer = document.createElement('div');
            versionsContainer.className = 'response-versions';
            versionsContainer.style.display = 'none';
            messageElement.appendChild(versionsContainer);
        }
    }
    
    // Scroll to bottom
    window.uiController.scrollToBottom();
    
    return messageId;
}

/**
 * Update an existing message
 * @param {string} messageId - ID of the message to update
 * @param {string} newContent - New message content
 * @param {boolean} [isEdited=false] - Whether to mark as edited
 * @returns {boolean} - Whether the update was successful
 */
function updateMessage(messageId, newContent, isEdited = false) {
    // Update in history
    const msgIndex = messageHistory.findIndex(msg => msg.id === messageId);
    if (msgIndex === -1) return false;
    
    messageHistory[msgIndex].content = newContent;
    
    // Update in UI
    const messageContainer = document.querySelector(`.message-container[data-message-id="${messageId}"]`);
    if (!messageContainer) return false;
    
    const messageDiv = messageContainer.querySelector('.message');
    if (!messageDiv) return false;
    
    messageDiv.innerHTML = window.messageFormatter.formatMarkdown(newContent);
    messageDiv.dataset.rawContent = newContent;
    
    // Update timestamp if edited
    if (isEdited) {
        const timestampDiv = messageDiv.querySelector('.message-timestamp');
        if (timestampDiv) {
            timestampDiv.textContent = window.messageFormatter.formatTimestamp(new Date(), true);
        }
    }
    
    return true;
}

/**
 * Enter edit mode for a message
 * @param {string} messageId - ID of the message to edit
 */
function enterEditMode(messageId) {
    const messageContainer = document.querySelector(`.message-container[data-message-id="${messageId}"]`);
    if (!messageContainer) return;
    
    const messageDiv = messageContainer.querySelector('.message');
    if (!messageDiv) return;
    
    const originalContent = messageDiv.dataset.rawContent || '';
    
    // Save the current state
    window.uiController.setCurrentlyEditing({
        id: messageId,
        container: messageContainer,
        originalContent: originalContent,
        originalHTML: messageContainer.innerHTML
    });
    
    // Create edit form
    const editForm = window.uiController.createEditForm(
        originalContent,
        saveEdit,
        cancelEdit
    );
    
    // Replace message with edit form
    messageContainer.innerHTML = '';
    messageContainer.appendChild(editForm);
    
    // Focus on textarea
    const textarea = editForm.querySelector('textarea');
    if (textarea) {
        textarea.focus();
    }
}

/**
 * Save an edited message
 * @param {string} newContent - New content for the message
 */
function saveEdit(newContent) {
    const currentlyEditing = window.uiController.getCurrentlyEditing();
    if (!currentlyEditing) return;
    
    const messageId = currentlyEditing.id;
    const messageContainer = currentlyEditing.container;
    
    // Update the message in history
    const messageIndex = messageHistory.findIndex(msg => msg.id === messageId);
    if (messageIndex !== -1) {
        messageHistory[messageIndex].content = newContent;
        
        // Create a new message div
        messageContainer.innerHTML = '';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message user-message`;
        messageDiv.innerHTML = window.messageFormatter.formatMarkdown(newContent);
        messageDiv.dataset.rawContent = newContent;
        
        // Add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        const now = new Date();
        timestampDiv.textContent = window.messageFormatter.formatTimestamp(now, true);
        messageDiv.appendChild(timestampDiv);
        
        // Add action buttons
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        const editBtn = document.createElement('button');
        editBtn.className = 'message-action-button';
        editBtn.innerHTML = '✏️';
        editBtn.title = 'Edit message';
        editBtn.onclick = () => enterEditMode(messageId);
        actionsDiv.appendChild(editBtn);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'message-action-button';
        deleteBtn.innerHTML = '🗑️';
        deleteBtn.title = 'Delete message';
        deleteBtn.onclick = () => deleteMessage(messageId);
        actionsDiv.appendChild(deleteBtn);
        
        messageDiv.appendChild(actionsDiv);
        messageContainer.appendChild(messageDiv);
        
        // Resend the message to get a new response
        window.wsClient.send({
            user_id: window.appConfig.userId,
            message: newContent,
            conversation_id: window.conversationManager.getCurrentConversationId(),
            edit: true,
            original_message_id: messageId
        });
    }
    
    window.uiController.clearCurrentlyEditing();
}

/**
 * Cancel editing a message
 */
function cancelEdit() {
    const currentlyEditing = window.uiController.getCurrentlyEditing();
    if (!currentlyEditing) return;
    
    // Restore original content
    currentlyEditing.container.innerHTML = currentlyEditing.originalHTML;
    window.uiController.clearCurrentlyEditing();
}

/**
 * Delete a message
 * @param {string} messageId - ID of the message to delete
 * @returns {boolean} - Whether the deletion was successful
 */
function deleteMessage(messageId) {
    if (!confirm('Are you sure you want to delete this message?')) return false;
    
    const messageContainer = document.querySelector(`.message-container[data-message-id="${messageId}"]`);
    if (!messageContainer) return false;
    
    // If this is a user message, also delete the assistant response if exists
    const nextContainer = messageContainer.nextElementSibling;
    if (nextContainer && nextContainer.querySelector('.assistant-message')) {
        nextContainer.remove();
    }
    
    // Remove from history
    const messageIndex = messageHistory.findIndex(msg => msg.id === messageId);
    if (messageIndex !== -1) {
        messageHistory.splice(messageIndex, 1);
    }
    
    // Remove from DOM
    messageContainer.remove();
    return true;
}

/**
 * Get all messages
 * @returns {Array} - Array of message objects
 */
function getAllMessages() {
    return [...messageHistory];
}

/**
 * Clear message history
 */
function clearMessages() {
    messageHistory = [];
}

/**
 * Send a user message via WebSocket
 * @param {string} message - Message content to send
 * @returns {boolean} - Whether the message was successfully sent
 */
function sendUserMessage(message) {
    if (!message.trim()) return false;
    
    // Add to UI first
    const messageId = addMessage(message, 'user');
    
    // Then send to server
    return window.wsClient.send({
        user_id: window.appConfig.userId,
        message: message,
        conversation_id: window.conversationManager.getCurrentConversationId(),
        message_id: messageId
    });
}

// Export message handlers for use in other modules
window.messageHandlers = {
    addMessage,
    updateMessage,
    enterEditMode,
    saveEdit,
    cancelEdit,
    deleteMessage,
    getAllMessages,
    clearMessages,
    sendUserMessage
};