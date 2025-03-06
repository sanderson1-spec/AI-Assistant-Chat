/**
 * ui-controller.js - Handles UI creation and updates
 */

// Module variables
let currentlyEditing = null;

/**
 * Create a message element
 * @param {string} content - Message content
 * @param {string} role - Message role (user, assistant, system)
 * @param {string} messageId - Unique message ID
 * @param {boolean} isEdited - Whether this message has been edited
 * @returns {HTMLElement} - The created message element
 */
function createMessageElement(content, role, messageId, isEdited = false) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';
    messageContainer.dataset.messageId = messageId;
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    messageDiv.innerHTML = window.messageFormatter.formatMarkdown(content);
    messageDiv.dataset.rawContent = content;
    
    // Add timestamp
    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-timestamp';
    timestampDiv.textContent = window.messageFormatter.formatTimestamp(new Date(), isEdited);
    messageDiv.appendChild(timestampDiv);
    
    // Add action buttons for user messages
    if (role === 'user') {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        // Edit button
        const editBtn = document.createElement('button');
        editBtn.className = 'message-action-button';
        editBtn.innerHTML = '✏️';
        editBtn.title = 'Edit message';
        editBtn.onclick = () => window.messageHandlers.enterEditMode(messageId);
        actionsDiv.appendChild(editBtn);
        
        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'message-action-button';
        deleteBtn.innerHTML = '🗑️';
        deleteBtn.title = 'Delete message';
        deleteBtn.onclick = () => window.messageHandlers.deleteMessage(messageId);
        actionsDiv.appendChild(deleteBtn);
        
        messageDiv.appendChild(actionsDiv);
    }
    
    messageContainer.appendChild(messageDiv);
    return messageContainer;
}

/**
 * Create a regenerate button for assistant messages
 * @param {string} userMessageId - ID of the user message to regenerate response for
 * @returns {HTMLElement} - Regenerate button element
 */
function createRegenerateButton(userMessageId) {
    const regenerateBtn = document.createElement('button');
    regenerateBtn.className = 'regenerate-button';
    regenerateBtn.innerHTML = '🔄 Regenerate response';
    regenerateBtn.onclick = () => window.conversationManager.regenerateResponse(userMessageId);
    return regenerateBtn;
}

/**
 * Create version controls for assistant messages with multiple versions
 * @param {string} userMessageId - ID of the user message
 * @param {number} currentVersion - Current active version index
 * @param {number} totalVersions - Total number of versions
 * @returns {HTMLElement} - Version controls container
 */
function createVersionControls(userMessageId, currentVersion, totalVersions) {
    const versionsContainer = document.createElement('div');
    versionsContainer.className = 'response-versions';
    
    if (totalVersions <= 1) {
        versionsContainer.style.display = 'none';
        return versionsContainer;
    }
    
    // Add version info
    const versionInfo = document.createElement('span');
    versionInfo.className = 'version-info';
    versionInfo.textContent = `${totalVersions} versions`;
    versionsContainer.appendChild(versionInfo);
    
    // Add version buttons
    for (let i = 0; i < totalVersions; i++) {
        const versionBtn = document.createElement('button');
        versionBtn.className = `version-button ${i === currentVersion ? 'active' : ''}`;
        versionBtn.textContent = `V${i + 1}`;
        versionBtn.onclick = () => window.conversationManager.switchResponseVersion(userMessageId, i);
        versionsContainer.appendChild(versionBtn);
    }
    
    return versionsContainer;
}

/**
 * Create the edit form for editing a message
 * @param {string} originalContent - Original message content
 * @param {function} onSave - Save callback function
 * @param {function} onCancel - Cancel callback function
 * @returns {HTMLElement} - Edit form element
 */
function createEditForm(originalContent, onSave, onCancel) {
    const editForm = document.createElement('div');
    editForm.className = 'edit-form';
    
    const textarea = document.createElement('textarea');
    textarea.className = 'edit-input';
    textarea.value = originalContent;
    textarea.rows = 3;
    
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'edit-actions';
    
    const saveBtn = document.createElement('button');
    saveBtn.className = 'save-edit';
    saveBtn.textContent = 'Save';
    saveBtn.onclick = () => onSave(textarea.value);
    
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'cancel-edit';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onclick = onCancel;
    
    actionsDiv.appendChild(cancelBtn);
    actionsDiv.appendChild(saveBtn);
    
    editForm.appendChild(textarea);
    editForm.appendChild(actionsDiv);
    
    return editForm;
}

/**
 * Create a conversation item for the sidebar
 * @param {object} conversation - Conversation data
 * @param {function} onSelect - Callback when conversation is selected
 * @param {function} onDelete - Callback when conversation is deleted
 * @returns {HTMLElement} - Conversation item element
 */
function createConversationItem(conversation, onSelect, onDelete) {
    const convDiv = document.createElement('div');
    convDiv.className = 'conversation-item';
    
    // Create title span
    const titleSpan = document.createElement('span');
    titleSpan.textContent = conversation.title;
    titleSpan.className = 'conversation-title';
    titleSpan.onclick = () => onSelect(conversation.conversation_id);
    
    // Create delete button
    const deleteButton = document.createElement('button');
    deleteButton.innerHTML = '&times;';
    deleteButton.className = 'delete-button';
    deleteButton.onclick = (e) => {
        e.stopPropagation(); // Prevent triggering the conversation loading
        onDelete(conversation.conversation_id);
    };
    
    // Add both to the conversation item
    convDiv.appendChild(titleSpan);
    convDiv.appendChild(deleteButton);
    
    return convDiv;
}

/**
 * Update the versions UI for a response
 * @param {HTMLElement} container - Container element
 * @param {string} userMessageId - User message ID
 * @param {number} activeVersion - Active version index
 * @param {number} totalVersions - Total versions count
 */
function updateVersionsUI(container, userMessageId, activeVersion, totalVersions) {
    // Find or create versions container
    let versionsContainer = container.querySelector('.response-versions');
    if (!versionsContainer) {
        versionsContainer = document.createElement('div');
        versionsContainer.className = 'response-versions';
        container.appendChild(versionsContainer);
    }
    
    // Update versions UI
    if (totalVersions <= 1) {
        versionsContainer.style.display = 'none';
        return;
    }
    
    versionsContainer.style.display = 'flex';
    versionsContainer.innerHTML = '';
    
    // Add version info
    const versionInfo = document.createElement('span');
    versionInfo.className = 'version-info';
    versionInfo.textContent = `${totalVersions} versions`;
    versionsContainer.appendChild(versionInfo);
    
    // Add version buttons
    for (let i = 0; i < totalVersions; i++) {
        const versionBtn = document.createElement('button');
        versionBtn.className = `version-button ${i === activeVersion ? 'active' : ''}`;
        versionBtn.textContent = `V${i + 1}`;
        versionBtn.onclick = () => window.conversationManager.switchResponseVersion(userMessageId, i);
        versionsContainer.appendChild(versionBtn);
    }
}

/**
 * Set the currently editing message
 * @param {object} editingInfo - Information about the message being edited
 */
function setCurrentlyEditing(editingInfo) {
    currentlyEditing = editingInfo;
}

/**
 * Get the currently editing message info
 * @returns {object|null} - Info about the message being edited
 */
function getCurrentlyEditing() {
    return currentlyEditing;
}

/**
 * Clear the currently editing state
 */
function clearCurrentlyEditing() {
    currentlyEditing = null;
}

/**
 * Scroll chat to the bottom
 */
function scrollToBottom() {
    const chatContainer = window.chatUtils.getElement('chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Export UI controller functions for use in other modules
window.uiController = {
    createMessageElement,
    createRegenerateButton,
    createVersionControls,
    createEditForm,
    createConversationItem,
    updateVersionsUI,
    setCurrentlyEditing,
    getCurrentlyEditing,
    clearCurrentlyEditing,
    scrollToBottom
};