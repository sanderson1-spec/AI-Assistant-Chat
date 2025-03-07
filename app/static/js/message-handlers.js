/**
 * Message creation and handling
 */
import MessageFormatter from './message-formatter.js';
import UIController from './ui-controller.js';
import ConversationManager from './conversation-manager.js';
import WebSocketManager from './websocket.js';

const MessageHandler = {
    lastUserMessageId: null,
    lastResponseId: null,
    currentEditingMessageId: null,
    
    /**
     * Process and display a new user message
     * @param {string} messageText - The message text
     * @param {string} userId - The user ID
     * @param {string|null} conversationId - The conversation ID, if any
     * @returns {Object} Message data object
     */
    sendUserMessage: function(messageText, userId, conversationId) {
        if (!messageText.trim()) return false;
        
        // If we're in editing mode, save the edit instead
        if (this.currentEditingMessageId) {
            this.saveMessageEdit(this.currentEditingMessageId, messageText);
            return null; // Editing messages don't generate a new message object
        }
        
        // Create temporary ID for the message before server assigns one
        const tempId = 'temp-' + Date.now();
        
        // Display the message in the UI
        const messageElement = this.createMessageElement({
            id: tempId,
            content: messageText,
            role: 'user'
        });
        
        UIController.addMessageToChat(messageElement);
        
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
        console.log('Handling incoming message:', data);
        
        if (data.edit_message_id) {
            // Replace the existing message
            this.replaceMessage(data.edit_message_id, data);
            
            // If we were in editing mode, exit that mode
            if (this.currentEditingMessageId) {
                this.exitEditingMode();
            }
        } else {
            // Add new message
            const messageElement = this.createMessageElement(data);
            UIController.addMessageToChat(messageElement);
        }
        
        if (data.conversation_id) {
            ConversationManager.setCurrentConversationId(data.conversation_id);
            ConversationManager.loadConversations();
        }
        
        // Keep track of message IDs for regeneration
        if (data.role === 'user') {
            this.lastUserMessageId = data.id;
        } else if (data.role === 'assistant') {
            this.lastResponseId = data.id;
        }
    },
    
    /**
     * Create a message element with actions based on the role
     * @param {Object} data - Message data
     * @returns {HTMLElement} The message element
     */
    createMessageElement: function(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.role}-message`;
        messageDiv.setAttribute('data-message-id', data.id);
        
        // Add parent ID reference if available
        if (data.parent_id) {
            messageDiv.setAttribute('data-parent-id', data.parent_id);
        }
        
        // Create content div
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = MessageFormatter.parseMarkdown(data.content);
        messageDiv.appendChild(contentDiv);
        
        // Add edited indicator if needed
        if (data.is_edited) {
            const editedSpan = document.createElement('div');
            editedSpan.className = 'edited-indicator';
            editedSpan.textContent = '(edited)';
            messageDiv.appendChild(editedSpan);
        }
        
        // Add action buttons based on role
        if (data.role === 'user') {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';
            
            const editButton = document.createElement('button');
            editButton.className = 'action-button';
            editButton.textContent = 'Edit';
            editButton.onclick = () => this.enterEditingMode(data.id, data.content);
            
            actionsDiv.appendChild(editButton);
            messageDiv.appendChild(actionsDiv);
        } else if (data.role === 'assistant' && data.parent_id) {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'message-actions';
            
            const regenerateButton = document.createElement('button');
            regenerateButton.className = 'action-button';
            regenerateButton.textContent = 'Regenerate';
            regenerateButton.onclick = () => this.regenerateResponse(data.parent_id);
            
            const versionsButton = document.createElement('button');
            versionsButton.className = 'action-button';
            versionsButton.textContent = 'Versions';
            versionsButton.onclick = () => this.toggleVersionSelector(data.parent_id);
            
            actionsDiv.appendChild(regenerateButton);
            actionsDiv.appendChild(versionsButton);
            messageDiv.appendChild(actionsDiv);
        }
        
        return messageDiv;
    },
    
    /**
     * Replace an existing message with updated content
     * @param {string|number} messageId - The message ID
     * @param {Object} data - The updated message data
     */
    replaceMessage: function(messageId, data) {
        const messageDiv = document.querySelector(`.message[data-message-id="${messageId}"]`);
        if (messageDiv) {
            // Update content
            const contentDiv = messageDiv.querySelector('.message-content');
            if (contentDiv) {
                contentDiv.innerHTML = MessageFormatter.parseMarkdown(data.content);
            }
            
            // Add edited indicator if not already present
            if (!messageDiv.querySelector('.edited-indicator') && data.is_edited) {
                const editedSpan = document.createElement('div');
                editedSpan.className = 'edited-indicator';
                editedSpan.textContent = '(edited)';
                messageDiv.appendChild(editedSpan);
            }
        } else {
            // If message doesn't exist, add it as new
            const messageElement = this.createMessageElement({
                id: messageId,
                content: data.content,
                role: data.role,
                is_edited: true
            });
            UIController.addMessageToChat(messageElement);
        }
    },
    
    /**
     * Enter editing mode for a message
     * @param {string|number} messageId - The message ID
     * @param {string} content - The current message content
     */
    enterEditingMode: function(messageId, content) {
        // Exit any existing editing mode first
        this.exitEditingMode();
        
        // Find the message
        const messageDiv = document.querySelector(`.message[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        // Add editing class
        messageDiv.classList.add('editing');
        
        // Replace content with textarea
        const contentDiv = messageDiv.querySelector('.message-content');
        const originalContent = contentDiv.textContent || '';
        contentDiv.innerHTML = '';
        
        const textarea = document.createElement('textarea');
        textarea.value = originalContent;
        textarea.style.width = '100%';
        textarea.style.minHeight = '40px';
        textarea.className = 'edit-textarea';
        contentDiv.appendChild(textarea);
        
        // Add save/cancel buttons
        const actionButtons = document.createElement('div');
        actionButtons.className = 'edit-actions';
        
        const saveButton = document.createElement('button');
        saveButton.textContent = 'Save';
        saveButton.onclick = () => this.saveMessageEdit(messageId, textarea.value);
        
        const cancelButton = document.createElement('button');
        cancelButton.textContent = 'Cancel';
        cancelButton.onclick = () => this.cancelMessageEdit(messageId, originalContent);
        
        actionButtons.appendChild(saveButton);
        actionButtons.appendChild(cancelButton);
        contentDiv.appendChild(actionButtons);
        
        // Focus the textarea
        textarea.focus();
        
        // Set current editing state
        this.currentEditingMessageId = messageId;
    },
    
    /**
     * Exit editing mode
     */
    exitEditingMode: function() {
        if (!this.currentEditingMessageId) return;
        
        const messageDiv = document.querySelector(`.message[data-message-id="${this.currentEditingMessageId}"]`);
        if (messageDiv) {
            messageDiv.classList.remove('editing');
            
            // Check if we still have an edit textarea, and if so, restore original content from it
            const textarea = messageDiv.querySelector('.edit-textarea');
            if (textarea) {
                const contentDiv = messageDiv.querySelector('.message-content');
                contentDiv.innerHTML = MessageFormatter.parseMarkdown(textarea.value);
            }
            
            // Remove edit actions
            const actionsDiv = messageDiv.querySelector('.edit-actions');
            if (actionsDiv) {
                actionsDiv.remove();
            }
        }
        
        this.currentEditingMessageId = null;
    },
    
    /**
     * Save edited message
     * @param {string|number} messageId - The message ID
     * @param {string} newContent - The new message content
     */
    saveMessageEdit: function(messageId, newContent) {
        try {
            // First, update UI immediately to show responsiveness
            const messageDiv = document.querySelector(`.message[data-message-id="${messageId}"]`);
            if (messageDiv) {
                const contentDiv = messageDiv.querySelector('.message-content');
                contentDiv.innerHTML = MessageFormatter.parseMarkdown(newContent);
                messageDiv.classList.remove('editing');
            }
            
            // Send the edit to the server
            if (WebSocketManager.isConnected()) {
                // For WebSocket, we'll send a special message with edit_message_id
                WebSocketManager.sendMessage({
                    user_id: ConversationManager.getUserId(),
                    message: newContent,
                    conversation_id: ConversationManager.getCurrentConversationId(),
                    edit_message_id: messageId
                });
            } else {
                // Fallback to REST API
                this.sendEditRequest(messageId, newContent);
            }
            
            // Exit editing mode
            this.currentEditingMessageId = null;
            
        } catch (error) {
            console.error('Error saving edit:', error);
            this.displaySystemMessage('Failed to save your edit. Please try again.');
        }
    },
    
    /**
     * Send edit request to the API
     * @param {string|number} messageId - The message ID
     * @param {string} newContent - The new content
     */
    sendEditRequest: function(messageId, newContent) {
        return fetch(`/api/messages/${messageId}/edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message_id: messageId,
                content: newContent
            })
        }).then(response => {
            if (!response.ok) {
                throw new Error('Failed to update message');
            }
            return response.json();
        });
    },
    
    /**
     * Cancel message editing and restore original content
     * @param {string|number} messageId - The message ID
     * @param {string} originalContent - The original message content
     */
    cancelMessageEdit: function(messageId, originalContent) {
        const messageDiv = document.querySelector(`.message[data-message-id="${messageId}"]`);
        if (messageDiv) {
            const contentDiv = messageDiv.querySelector('.message-content');
            contentDiv.innerHTML = MessageFormatter.parseMarkdown(originalContent);
            messageDiv.classList.remove('editing');
        }
        
        this.currentEditingMessageId = null;
    },
    
    /**
     * Regenerate response for a message
     * @param {string|number} parentId - The parent message ID
     */
    regenerateResponse: function(parentId) {
        // Show loading indicator
        const responseElements = document.querySelectorAll(`.message[data-parent-id="${parentId}"]`);
        if (responseElements.length > 0) {
            // Get the latest response (should be only one visible)
            const responseDiv = responseElements[0];
            const contentDiv = responseDiv.querySelector('.message-content');
            const originalContent = contentDiv.textContent || '';
            contentDiv.textContent = 'Regenerating...';
            
            // Call the regenerate API
            this.sendRegenerateRequest(parentId)
                .then(data => {
                    // Update the UI with the new response
                    contentDiv.innerHTML = MessageFormatter.parseMarkdown(data.content);
                    
                    // Add version selector after regenerating
                    this.loadAndShowVersionSelector(parentId);
                })
                .catch(error => {
                    console.error('Error regenerating response:', error);
                    contentDiv.textContent = originalContent;
                    this.displaySystemMessage('Failed to regenerate response. Please try again.');
                });
        }
    },
    
    /**
     * Send regenerate request to the API
     * @param {string|number} parentId - The parent message ID
     * @returns {Promise} The fetch promise
     */
    sendRegenerateRequest: function(parentId) {
        return fetch(`/api/messages/${parentId}/regenerate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message_id: parentId,
                conversation_id: ConversationManager.getCurrentConversationId(),
                user_id: ConversationManager.getUserId()
            })
        }).then(response => {
            if (!response.ok) {
                throw new Error('Failed to regenerate response');
            }
            return response.json();
        });
    },
    
    /**
     * Load response versions and show selector
     * @param {string|number} parentId - The parent message ID
     */
    loadAndShowVersionSelector: function(parentId) {
        fetch(`/api/messages/${parentId}/versions`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to load versions');
                }
                return response.json();
            })
            .then(data => {
                if (data.versions && data.versions.length > 1) {
                    this.showVersionSelector(parentId, data.versions);
                }
            })
            .catch(error => {
                console.error('Error loading versions:', error);
            });
    },
    
    /**
     * Show version selector UI
     * @param {string|number} parentId - The parent message ID
     * @param {Array} versions - Array of version objects
     */
    showVersionSelector: function(parentId, versions) {
        // Find the message where we'll add the version selector
        const messageElements = document.querySelectorAll(`.message[data-parent-id="${parentId}"]`);
        if (messageElements.length === 0) return;
        
        const messageDiv = messageElements[0];
        
        // Remove existing version selector if present
        const existingSelector = messageDiv.querySelector('.version-selector');
        if (existingSelector) {
            existingSelector.remove();
        }
        
        // Create the version selector
        const selectorDiv = document.createElement('div');
        selectorDiv.className = 'version-selector';
        selectorDiv.innerHTML = '<span>Versions: </span>';
        
        versions.forEach(version => {
            const versionButton = document.createElement('button');
            versionButton.className = `version-button ${version.is_active ? 'active' : ''}`;
            versionButton.textContent = `V${version.version}`;
            versionButton.onclick = () => this.selectVersion(version.id, parentId, version.content);
            selectorDiv.appendChild(versionButton);
        });
        
        // Insert at the top of the message
        messageDiv.insertBefore(selectorDiv, messageDiv.firstChild);
    },
    
    /**
     * Toggle visibility of version selector
     * @param {string|number} parentId - The parent message ID
     */
    toggleVersionSelector: function(parentId) {
        const messageDiv = document.querySelector(`.message[data-parent-id="${parentId}"]`);
        if (!messageDiv) return;
        
        const existingSelector = messageDiv.querySelector('.version-selector');
        if (existingSelector) {
            // If selector exists, toggle it
            existingSelector.style.display = existingSelector.style.display === 'none' ? 'flex' : 'none';
        } else {
            // Load versions and show selector
            this.loadAndShowVersionSelector(parentId);
        }
    },
    
    /**
     * Select a specific response version
     * @param {string|number} messageId - The message ID
     * @param {string|number} parentId - The parent message ID
     * @param {string} content - The message content
     */
    selectVersion: function(messageId, parentId, content) {
        try {
            // Update UI immediately
            const messageDiv = document.querySelector(`.message[data-parent-id="${parentId}"]`);
            if (messageDiv) {
                const contentDiv = messageDiv.querySelector('.message-content');
                contentDiv.innerHTML = MessageFormatter.parseMarkdown(content);
                
                // Update active button
                const versionButtons = messageDiv.querySelectorAll('.version-button');
                versionButtons.forEach(button => {
                    button.classList.remove('active');
                });
                
                // Find and mark the clicked button as active
                Array.from(versionButtons).find(button => 
                    button.onclick.toString().includes(messageId)
                )?.classList.add('active');
            }
            
            // Send selection to server
            this.sendSelectVersionRequest(messageId, parentId);
            
        } catch (error) {
            console.error('Error selecting version:', error);
            this.displaySystemMessage('Failed to select version. Please try again.');
        }
    },
    
    /**
     * Send select version request to the API
     * @param {string|number} messageId - The message ID
     * @param {string|number} parentId - The parent message ID
     * @returns {Promise} The fetch promise
     */
    sendSelectVersionRequest: function(messageId, parentId) {
        return fetch('/api/messages/select-version', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message_id: messageId,
                parent_id: parentId,
                conversation_id: ConversationManager.getCurrentConversationId(),
                user_id: ConversationManager.getUserId()
            })
        }).then(response => {
            if (!response.ok) {
                throw new Error('Failed to select version');
            }
            return response.json();
        });
    },
    
    /**
     * Display a message in the chat UI using the original message object
     * @param {string} content - The message content
     * @param {string} role - The role (user/assistant)
     */
    displayMessage: function(content, role) {
        const messageElement = this.createMessageElement({
            id: 'manual-' + Date.now(),
            content: content,
            role: role
        });
        UIController.addMessageToChat(messageElement);
    },
    
    /**
     * Display a system message in the chat
     * @param {string} message - The system message
     */
    displaySystemMessage: function(message) {
        this.displayMessage(message, 'system');
    },
    
    /**
     * Handle keyboard shortcuts for message actions
     * @param {KeyboardEvent} event - Keyboard event
     */
    handleKeyboardShortcuts: function(event) {
        // Cmd+R to regenerate last response
        if ((event.metaKey || event.ctrlKey) && event.key === 'r') {
            event.preventDefault();
            if (this.lastUserMessageId) {
                this.regenerateResponse(this.lastUserMessageId);
            }
        }
        
        // Escape to cancel editing
        if (event.key === 'Escape' && this.currentEditingMessageId) {
            this.exitEditingMode();
        }
    }
};

// Set up global keyboard shortcuts
document.addEventListener('keydown', (event) => {
    MessageHandler.handleKeyboardShortcuts(event);
});

export default MessageHandler;