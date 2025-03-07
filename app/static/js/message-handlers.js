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
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        if (data.role === 'user') {
            // User message actions
            const editButton = document.createElement('button');
            editButton.className = 'action-button';
            editButton.textContent = 'Edit';
            editButton.onclick = () => this.enterEditingMode(data.id, data.content);
            
            const deleteButton = document.createElement('button');
            deleteButton.className = 'action-button delete-action';
            deleteButton.textContent = 'Delete';
            deleteButton.onclick = () => this.deleteMessage(data.id);
            
            const rewindButton = document.createElement('button');
            rewindButton.className = 'action-button rewind-action';
            rewindButton.textContent = 'Rewind';
            rewindButton.onclick = () => this.rewindToMessage(data.id);
            
            actionsDiv.appendChild(editButton);
            actionsDiv.appendChild(deleteButton);
            actionsDiv.appendChild(rewindButton);
        } else if (data.role === 'assistant' && data.parent_id) {
            // Assistant message actions
            const regenerateButton = document.createElement('button');
            regenerateButton.className = 'action-button';
            regenerateButton.textContent = 'Regenerate';
            regenerateButton.onclick = () => this.regenerateResponse(data.parent_id);
            
            const versionsButton = document.createElement('button');
            versionsButton.className = 'action-button';
            versionsButton.textContent = 'Versions';
            versionsButton.onclick = () => this.toggleVersionSelector(data.parent_id);
            
            const deleteButton = document.createElement('button');
            deleteButton.className = 'action-button delete-action';
            deleteButton.textContent = 'Delete';
            deleteButton.onclick = () => this.deleteMessage(data.id);
            
            actionsDiv.appendChild(regenerateButton);
            actionsDiv.appendChild(versionsButton);
            actionsDiv.appendChild(deleteButton);
        }
        
        // Only add actions div if there are buttons
        if (actionsDiv.children.length > 0) {
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
            this.displaySystemMessage('Failed to save your edit. Please try again.', 5000);
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
                    
                    // Show success message
                    this.displaySystemMessage('Response regenerated successfully', 2000);
                })
                .catch(error => {
                    console.error('Error regenerating response:', error);
                    contentDiv.textContent = originalContent;
                    this.displaySystemMessage('Failed to regenerate response. Please try again.', 5000);
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
            
            // Show brief confirmation
            this.displaySystemMessage('Version selected', 2000);
            
        } catch (error) {
            console.error('Error selecting version:', error);
            this.displaySystemMessage('Failed to select version. Please try again.', 5000);
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
     * Delete a message and its responses
     * @param {string|number} messageId - The message ID to delete
     */
    deleteMessage: function(messageId) {
        // Confirm deletion
        if (!confirm("Are you sure you want to delete this message? This cannot be undone.")) {
            return;
        }
        
        // Find the message element
        const messageDiv = document.querySelector(`.message[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        // If it's a user message, also find any response elements
        const role = messageDiv.classList.contains('user-message') ? 'user' : 'assistant';
        let responseElements = [];
        
        if (role === 'user') {
            // Find all responses that have this message as parent
            responseElements = document.querySelectorAll(`.message[data-parent-id="${messageId}"]`);
        }
        
        // Show loading state
        messageDiv.style.opacity = '0.5';
        messageDiv.style.pointerEvents = 'none';
        responseElements.forEach(el => {
            el.style.opacity = '0.5';
            el.style.pointerEvents = 'none';
        });
        
        // Check for temporary IDs
        if (messageId.toString().startsWith('temp-')) {
            this.displaySystemMessage('Cannot delete an unsaved message. Please wait for the message to be processed.', 5000);
            
            // Restore elements
            messageDiv.style.opacity = '1';
            messageDiv.style.pointerEvents = 'auto';
            responseElements.forEach(el => {
                el.style.opacity = '1';
                el.style.pointerEvents = 'auto';
            });
            
            return;
        }
        
        // Send delete request to server
        fetch(`/api/messages/${messageId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message_id: messageId,
                user_id: ConversationManager.getUserId()
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to delete message');
            }
            return response.json();
        })
        .then(data => {
            // Remove the message elements from DOM
            messageDiv.remove();
            responseElements.forEach(el => el.remove());
            
            // Also remove from lastUserMessageId/lastResponseId if it was the last one
            if (role === 'user' && this.lastUserMessageId == messageId) {
                this.lastUserMessageId = null;
            } else if (role === 'assistant' && this.lastResponseId == messageId) {
                this.lastResponseId = null;
            }
            
            // Show a brief success message
            this.displaySystemMessage('Message deleted successfully', 2000);
        })
        .catch(error => {
            console.error('Error deleting message:', error);
            
            // Restore elements
            messageDiv.style.opacity = '1';
            messageDiv.style.pointerEvents = 'auto';
            responseElements.forEach(el => {
                el.style.opacity = '1';
                el.style.pointerEvents = 'auto';
            });
            
            this.displaySystemMessage('Failed to delete message. Please try again.', 5000);
        });
    },
    
    /**
     * Rewind conversation to a specific message by deleting all later messages
     * @param {string|number} messageId - The message ID to rewind to
     */
    rewindToMessage: function(messageId) {
        // Confirm rewind
        if (!confirm("Rewind the conversation to this message? This will permanently delete all later messages.")) {
            return;
        }
        
        // Find the message element
        const messageDiv = document.querySelector(`.message[data-message-id="${messageId}"]`);
        if (!messageDiv) return;
        
        // Check if this is a temporary message ID (client-side only, not in database yet)
        if (messageId.toString().startsWith('temp-')) {
            this.displaySystemMessage('Cannot rewind to an unsaved message. Please wait for the message to be processed.', 5000);
            return;
        }
        
        // Show loading indicator (no auto-dismiss for this one since we'll replace it)
        const loadingMessageId = 'loading-' + Date.now();
        const loadingMessage = this.createMessageElement({
            id: loadingMessageId,
            content: 'Rewinding conversation...',
            role: 'system'
        });
        UIController.addMessageToChat(loadingMessage);
        
        // Send rewind request to server
        fetch(`/api/messages/${messageId}/rewind`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message_id: messageId,
                user_id: ConversationManager.getUserId()
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to rewind conversation: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            // Remove the loading message
            const loadingElement = document.querySelector(`.message[data-message-id="${loadingMessageId}"]`);
            if (loadingElement) {
                loadingElement.remove();
            }
            
            // If successful, reload the conversation
            UIController.clearChatMessages();
            
            // Reset message tracking
            this.lastUserMessageId = null;
            this.lastResponseId = null;
            
            // Add each message back to the UI
            data.messages.forEach(message => {
                const messageElement = this.createMessageElement(message);
                UIController.addMessageToChat(messageElement);
                
                // Track messages for regeneration
                if (message.role === 'user') {
                    this.lastUserMessageId = message.id;
                } else if (message.role === 'assistant') {
                    this.lastResponseId = message.id;
                }
            });
            
            // Display success message that auto-dismisses after 2 seconds
            this.displaySystemMessage('Conversation rewound successfully', 2000);
        })
        .catch(error => {
            // Remove the loading message
            const loadingElement = document.querySelector(`.message[data-message-id="${loadingMessageId}"]`);
            if (loadingElement) {
                loadingElement.remove();
            }
            
            console.error('Error rewinding conversation:', error);
            this.displaySystemMessage('Failed to rewind conversation. Please try again.', 5000);
        });
    },
    
    /**
     * Display a system message in the chat that auto-dismisses
     * @param {string} message - The system message
     * @param {number} timeout - Time in milliseconds before the message disappears (default 3000ms)
     */
    displaySystemMessage: function(message, timeout = 3000) {
        const messageId = 'system-' + Date.now();
        const messageElement = this.createMessageElement({
            id: messageId,
            content: message,
            role: 'system'
        });
        
        UIController.addMessageToChat(messageElement);
        
        // Auto-dismiss after timeout
        setTimeout(() => {
            const systemMessage = document.querySelector(`.message[data-message-id="${messageId}"]`);
            if (systemMessage) {
                // Add fade-out animation
                systemMessage.style.opacity = '0';
                systemMessage.style.transition = 'opacity 0.5s ease';
                
                // Remove from DOM after animation completes
                setTimeout(() => {
                    systemMessage.remove();
                }, 500); // 500ms for the fade-out animation
            }
        }, timeout);
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