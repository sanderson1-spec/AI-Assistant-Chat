// Global variables
const userId = 'default_user';
let currentConversationId = null;
let clientId = Math.random().toString(36).substring(2, 15);
let socket = null;
let messageHistory = [];
let currentlyEditing = null;
let responseVersions = {/**
 * Load a specific conversation
 */
async function loadConversation(conversationId) {
    try {
        currentConversationId = conversationId;
        const response = await fetch(`/api/conversations/${conversationId}`);
        const data = await response.json();
        
        const chatContainer = document.getElementById('chat-container');
        chatContainer.innerHTML = '';
        messageHistory = [];
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
                    timestamp: message.timestamp
                });
            }
        });
        
        // Display messages
        data.messages.forEach(message => {
            if (message.role === 'user') {
                addMessageToChat(message.content, message.role);
            } else if (message.role === 'assistant' && message.metadata && message.metadata.responseToId) {
                const userMsgId = message.metadata.responseToId;
                const versions = responseVersions[userMsgId];
                if (versions && versions.length > 0) {
                    // Show the latest version by default
                    const latestVersion = versions[versions.length - 1];
                    addOrUpdateAssistantMessage(latestVersion.content, userMsgId);
                }
            } else if (message.role === 'assistant') {
                // Regular assistant message (not a response to a specific user message)
                addMessageToChat(message.content, message.role);
            }
        });
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

/**
 * Delete a conversation
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
            body: JSON.stringify({ user_id: userId })
        });
        
        if (response.ok) {
            // If the deleted conversation was the current one, clear the chat
            if (currentConversationId === conversationId) {
                currentConversationId = null;
                document.getElementById('chat-container').innerHTML = '';
                messageHistory = [];
                responseVersions = {};
            }
            
            // Reload the conversations list
            loadConversations();
        } else {
            console.error('Failed to delete conversation');
        }
    } catch (error) {
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
        const response = await fetch(`/api/conversations?user_id=${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Clear current chat
            currentConversationId = null;
            document.getElementById('chat-container').innerHTML = '';
            messageHistory = [];
            responseVersions = {};
            
            // Reload conversations list (should be empty)
            loadConversations();
        } else {
            console.error('Failed to clear conversations');
        }
    } catch (error) {
        console.error('Error clearing conversations:', error);
    }
}

/**
 * Initialize the application
 */
function init() {
    // Connect WebSocket
    connectWebSocket();
    
    // Load conversations list
    loadConversations();
    
    // Set up button event listeners
    document.getElementById('send-button').addEventListener('click', sendMessage);
    
    document.getElementById('message-input').addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
    
    document.getElementById('new-chat-button').addEventListener('click', function() {
        currentConversationId = null;
        document.getElementById('chat-container').innerHTML = '';
        messageHistory = [];
        responseVersions = {};
    });
    
    // Handle keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Command+R (Mac) or Ctrl+R (Windows/Linux) for regenerating response
        if ((event.metaKey || event.ctrlKey) && event.key === 'r') {
            event.preventDefault(); // Prevent browser refresh
            
            // Find the last assistant message and regenerate it
            for (let i = messageHistory.length - 1; i >= 0; i--) {
                if (messageHistory[i].role === 'assistant' && messageHistory[i].responseToId) {
                    regenerateResponse(messageHistory[i].responseToId);
                    break;
                }
            }
        }
    });
}

// Initialize when the page is fully loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
};

/**
 * Convert text with simple Markdown syntax to HTML
 */
function formatMarkdown(text) {
    if (!text) return '';
    
    // Clone the text to avoid modifying the original
    let formattedText = text;
    
    // Replace *text* with <em>text</em> (italic)
    const italicRegex = /(?<!\*)\*([^*]+)\*(?!\*)/g;
    formattedText = formattedText.replace(italicRegex, '<em>$1</em>');
    
    // Replace **text** with <strong>text</strong> (bold)
    const boldRegex = /\*\*([^*]+)\*\*/g;
    formattedText = formattedText.replace(boldRegex, '<strong>$1</strong>');
    
    // Replace `code` with <code>code</code> (inline code)
    const codeRegex = /`([^`]+)`/g;
    formattedText = formattedText.replace(codeRegex, '<code>$1</code>');
    
    // Convert newlines to <br> tags
    formattedText = formattedText.replace(/\n/g, '<br>');
    
    return formattedText;
}

/**
 * Display debug messages in the console and optionally in the UI
 */
function showDebugMessage(message, isError = false) {
    console.log(message);
    // Optionally display in the UI for better visibility
    const chatContainer = document.getElementById('chat-container');
    const debugDiv = document.createElement('div');
    debugDiv.className = `debug-message ${isError ? 'error' : 'info'}`;
    debugDiv.textContent = `[Debug] ${message}`;
    chatContainer.appendChild(debugDiv);
}

/**
 * Connect to the WebSocket server
 */
function connectWebSocket() {
    try {
        const wsUrl = `ws://${window.location.host}/ws/${clientId}`;
        showDebugMessage(`Attempting to connect to WebSocket at ${wsUrl}`);
        socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            showDebugMessage('WebSocket connected successfully');
        };
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                // For new assistant messages, add to response versions
                if (data.role === 'assistant') {
                    const lastUserMsgIndex = findLastUserMessageIndex();
                    if (lastUserMsgIndex !== -1) {
                        const msgId = messageHistory[lastUserMsgIndex].id;
                        if (!responseVersions[msgId]) {
                            responseVersions[msgId] = [];
                        }
                        responseVersions[msgId].push({
                            content: data.content,
                            timestamp: new Date().toISOString()
                        });
                        
                        // Update the UI
                        addOrUpdateAssistantMessage(data.content, messageHistory[lastUserMsgIndex].id);
                    } else {
                        addMessageToChat(data.content, data.role);
                    }
                } else {
                    // For user messages
                    addMessageToChat(data.content, data.role);
                }
                
                if (data.conversation_id) {
                    currentConversationId = data.conversation_id;
                    loadConversations();
                }
            }
        };
        
        socket.onclose = (event) => {
            showDebugMessage(`WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason || 'No reason provided'}`, true);
            // Try to reconnect after a delay
            setTimeout(connectWebSocket, 3000);
        };
        
        socket.onerror = (error) => {
            showDebugMessage(`WebSocket error: ${error}`, true);
            console.error('WebSocket error:', error);
        };
    } catch (error) {
        showDebugMessage(`Exception during WebSocket connection: ${error.message}`, true);
        console.error('WebSocket connection error:', error);
    }
}

/**
 * Find the index of the last user message in the history
 */
function findLastUserMessageIndex() {
    for (let i = messageHistory.length - 1; i >= 0; i--) {
        if (messageHistory[i].role === 'user') {
            return i;
        }
    }
    return -1;
}

/**
 * Add a new message to the chat
 */
function addMessageToChat(content, role) {
    const chatContainer = document.getElementById('chat-container');
    const messageId = Date.now().toString();
    
    // Add to message history
    messageHistory.push({
        id: messageId,
        content: content,
        role: role,
        timestamp: new Date().toISOString()
    });
    
    // Create message container
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container';
    messageContainer.dataset.messageId = messageId;
    
    // Create message element
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    messageDiv.innerHTML = formatMarkdown(content);
    messageDiv.dataset.rawContent = content;
    
    // Add timestamp
    const timestampDiv = document.createElement('div');
    timestampDiv.className = 'message-timestamp';
    const now = new Date();
    timestampDiv.textContent = now.toLocaleTimeString();
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
        editBtn.onclick = () => enterEditMode(messageId);
        actionsDiv.appendChild(editBtn);
        
        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'message-action-button';
        deleteBtn.innerHTML = '🗑️';
        deleteBtn.title = 'Delete message';
        deleteBtn.onclick = () => deleteMessage(messageId);
        actionsDiv.appendChild(deleteBtn);
        
        messageDiv.appendChild(actionsDiv);
    }
    
    // Add regenerate button for assistant messages that follow a user message
    if (role === 'assistant' && messageHistory.length > 1) {
        // Find the preceding user message
        const prevMsg = messageHistory[messageHistory.length - 2];
        if (prevMsg && prevMsg.role === 'user') {
            const regenerateBtn = document.createElement('button');
            regenerateBtn.className = 'regenerate-button';
            regenerateBtn.innerHTML = '🔄 Regenerate response';
            regenerateBtn.onclick = () => regenerateResponse(prevMsg.id);
            
            // Create versions container
            const versionsContainer = document.createElement('div');
            versionsContainer.className = 'response-versions';
            versionsContainer.style.display = 'none'; // Initially hidden
            
            messageContainer.appendChild(messageDiv);
            messageContainer.appendChild(regenerateBtn);
            messageContainer.appendChild(versionsContainer);
            chatContainer.appendChild(messageContainer);
        } else {
            messageContainer.appendChild(messageDiv);
            chatContainer.appendChild(messageContainer);
        }
    } else {
        messageContainer.appendChild(messageDiv);
        chatContainer.appendChild(messageContainer);
    }
    
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Add or update an assistant message in response to a user message
 */
function addOrUpdateAssistantMessage(content, userMessageId) {
    const chatContainer = document.getElementById('chat-container');
    const messageId = Date.now().toString();
    
    // Check if this user message already has a response
    const versions = responseVersions[userMessageId];
    const versionIndex = versions.length - 1;
    
    // Find the message container after the user message
    const userMsgContainer = document.querySelector(`.message-container[data-message-id="${userMessageId}"]`);
    let assistantMsgContainer;
    
    if (userMsgContainer && userMsgContainer.nextElementSibling && 
        userMsgContainer.nextElementSibling.querySelector('.assistant-message')) {
        // Response exists, update it
        assistantMsgContainer = userMsgContainer.nextElementSibling;
        const messageDiv = assistantMsgContainer.querySelector('.message');
        messageDiv.innerHTML = formatMarkdown(content);
        messageDiv.dataset.rawContent = content;
        messageDiv.dataset.versionIndex = versionIndex;
        
        // Update timestamp
        const timestampDiv = messageDiv.querySelector('.message-timestamp');
        if (timestampDiv) {
            const now = new Date();
            timestampDiv.textContent = now.toLocaleTimeString();
        }
        
        // Update versions buttons
        updateVersionButtons(userMessageId, assistantMsgContainer);
    } else {
        // No response yet, create new
        assistantMsgContainer = document.createElement('div');
        assistantMsgContainer.className = 'message-container';
        assistantMsgContainer.dataset.responseToMessageId = userMessageId;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        messageDiv.innerHTML = formatMarkdown(content);
        messageDiv.dataset.rawContent = content;
        messageDiv.dataset.versionIndex = versionIndex;
        
        // Add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        const now = new Date();
        timestampDiv.textContent = now.toLocaleTimeString();
        messageDiv.appendChild(timestampDiv);
        
        // Create regenerate button
        const regenerateBtn = document.createElement('button');
        regenerateBtn.className = 'regenerate-button';
        regenerateBtn.innerHTML = '🔄 Regenerate response';
        regenerateBtn.onclick = () => regenerateResponse(userMessageId);
        
        // Create versions container
        const versionsContainer = document.createElement('div');
        versionsContainer.className = 'response-versions';
        
        assistantMsgContainer.appendChild(messageDiv);
        assistantMsgContainer.appendChild(regenerateBtn);
        assistantMsgContainer.appendChild(versionsContainer);
        
        // Add new response after the user message
        if (userMsgContainer && userMsgContainer.nextSibling) {
            chatContainer.insertBefore(assistantMsgContainer, userMsgContainer.nextSibling);
        } else {
            chatContainer.appendChild(assistantMsgContainer);
        }
        
        // Update message history
        if (!messageHistory.some(msg => msg.id === messageId)) {
            messageHistory.push({
                id: messageId,
                content: content,
                role: 'assistant',
                responseToId: userMessageId,
                timestamp: new Date().toISOString()
            });
        }
        
        // Update version buttons
        updateVersionButtons(userMessageId, assistantMsgContainer);
    }
    
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * Update the version buttons for a response
 */
function updateVersionButtons(userMessageId, assistantMsgContainer) {
    const versions = responseVersions[userMessageId];
    const versionsContainer = assistantMsgContainer.querySelector('.response-versions');
    const currentVersionIndex = parseInt(assistantMsgContainer.querySelector('.message').dataset.versionIndex);
    
    if (!versions || versions.length <= 1) {
        versionsContainer.style.display = 'none';
        return;
    }
    
    // Show versions container if we have multiple versions
    versionsContainer.style.display = 'flex';
    versionsContainer.innerHTML = '';
    
    // Add version info
    const versionInfo = document.createElement('span');
    versionInfo.className = 'version-info';
    versionInfo.textContent = `${versions.length} versions`;
    versionsContainer.appendChild(versionInfo);
    
    // Add version buttons
    versions.forEach((version, index) => {
        const versionBtn = document.createElement('button');
        versionBtn.className = `version-button ${index === currentVersionIndex ? 'active' : ''}`;
        versionBtn.textContent = `V${index + 1}`;
        versionBtn.onclick = () => switchResponseVersion(userMessageId, index);
        versionsContainer.appendChild(versionBtn);
    });
}

/**
 * Switch between different versions of a response
 */
function switchResponseVersion(userMessageId, versionIndex) {
    const versions = responseVersions[userMessageId];
    if (!versions || versionIndex >= versions.length) return;
    
    const assistantMsgContainer = document.querySelector(`.message-container[data-response-to-message-id="${userMessageId}"]`);
    if (!assistantMsgContainer) return;
    
    const messageDiv = assistantMsgContainer.querySelector('.message');
    messageDiv.innerHTML = formatMarkdown(versions[versionIndex].content);
    messageDiv.dataset.rawContent = versions[versionIndex].content;
    messageDiv.dataset.versionIndex = versionIndex;
    
    // Update version buttons
    const versionButtons = assistantMsgContainer.querySelectorAll('.version-button');
    versionButtons.forEach((btn, idx) => {
        btn.classList.toggle('active', idx === versionIndex);
    });
}

/**
 * Regenerate a response to a user message
 */
function regenerateResponse(userMessageId) {
    // Find the user message
    const userMsg = messageHistory.find(msg => msg.id === userMessageId);
    if (!userMsg) return;
    
    // Send the message again to get a new response
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            user_id: userId,
            message: userMsg.content,
            conversation_id: currentConversationId,
            regenerate: true
        }));
    } else {
        console.error('WebSocket not connected');
    }
}

/**
 * Enter edit mode for a message
 */
function enterEditMode(messageId) {
    const messageContainer = document.querySelector(`.message-container[data-message-id="${messageId}"]`);
    if (!messageContainer) return;
    
    const messageDiv = messageContainer.querySelector('.message');
    const originalContent = messageDiv.dataset.rawContent;
    
    // Save the current state
    currentlyEditing = {
        id: messageId,
        container: messageContainer,
        originalContent: originalContent,
        originalHTML: messageContainer.innerHTML
    };
    
    // Create edit form
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
    saveBtn.onclick = () => saveEdit(textarea.value);
    
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'cancel-edit';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.onclick = cancelEdit;
    
    actionsDiv.appendChild(cancelBtn);
    actionsDiv.appendChild(saveBtn);
    
    editForm.appendChild(textarea);
    editForm.appendChild(actionsDiv);
    
    // Replace message with edit form
    messageContainer.innerHTML = '';
    messageContainer.appendChild(editForm);
    
    // Focus on textarea
    textarea.focus();
}

/**
 * Save an edited message
 */
function saveEdit(newContent) {
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
        messageDiv.innerHTML = formatMarkdown(newContent);
        messageDiv.dataset.rawContent = newContent;
        
        // Add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        const now = new Date();
        timestampDiv.textContent = now.toLocaleTimeString() + ' (edited)';
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
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                user_id: userId,
                message: newContent,
                conversation_id: currentConversationId,
                edit: true,
                original_message_id: messageId
            }));
        }
    }
    
    currentlyEditing = null;
}

/**
 * Cancel editing a message
 */
function cancelEdit() {
    if (!currentlyEditing) return;
    
    // Restore original content
    currentlyEditing.container.innerHTML = currentlyEditing.originalHTML;
    currentlyEditing = null;
}

/**
 * Delete a message
 */
function deleteMessage(messageId) {
    if (!confirm('Are you sure you want to delete this message?')) return;
    
    const messageContainer = document.querySelector(`.message-container[data-message-id="${messageId}"]`);
    if (!messageContainer) return;
    
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
}

/**
 * Send a message to the server
 */
function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    
    // Check WebSocket connection
    if (socket && socket.readyState === WebSocket.OPEN) {
        try {
            // Prepare payload
            const payload = {
                user_id: userId,
                message: message,
                conversation_id: currentConversationId
            };
            
            showDebugMessage(`Sending message: ${JSON.stringify(payload).substring(0, 50)}...`);
            
            // Send message through WebSocket
            socket.send(JSON.stringify(payload));
        } catch (error) {
            showDebugMessage(`Error sending message: ${error.message}`, true);
            addMessageToChat('Error: Failed to send message. Please try again.', 'system');
        }
    } else {
        showDebugMessage(`WebSocket not connected. Current state: ${socket ? socket.readyState : 'No socket'}`, true);
        addMessageToChat('Error: Cannot connect to server. Please refresh the page.', 'system');
        
        // Try to reconnect
        connectWebSocket();
    }
    
    // Clear input field
    messageInput.value = '';
}

/**
 * Load the list of conversations from the server
 */
async function loadConversations() {
    try {
        const response = await fetch(`/api/conversations?user_id=${userId}`);
        const data = await response.json();
        
        const conversationsList = document.getElementById('conversations-list');
        conversationsList.innerHTML = '';
        
        data.conversations.forEach(conv => {
            const convDiv = document.createElement('div');
            convDiv.className = 'conversation-item';
            
            // Create title span
            const titleSpan = document.createElement('span');
            titleSpan.textContent = conv.title;
            titleSpan.className = 'conversation-title';
            titleSpan.onclick = () => loadConversation(conv.conversation_id);
            
            // Create delete button
            const deleteButton = document.createElement('button');
            deleteButton.innerHTML = '&times;';
            deleteButton.className = 'delete-button';
            deleteButton.onclick = (e) => {
                e.stopPropagation(); // Prevent triggering the conversation loading
                deleteConversation(conv.conversation_id);
            };
            
            // Add both to the conversation item
            convDiv.appendChild(titleSpan);
            convDiv.appendChild(deleteButton);
            
            conversationsList.appendChild(convDiv);
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
        console.error('Error loading conversations:', error);
    }
}