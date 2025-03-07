/**
 * UI updates and DOM manipulation
 */

const UIController = {
    /**
     * Add a message element to the chat container
     * @param {HTMLElement} messageElement - The message element to add
     */
    addMessageToChat: function(messageElement) {
        const chatContainer = document.getElementById('chat-container');
        chatContainer.appendChild(messageElement);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    },
    
    /**
     * Clear all messages from the chat container
     */
    clearChatMessages: function() {
        document.getElementById('chat-container').innerHTML = '';
    },
    
    /**
     * Get the value from the message input field
     * @returns {string} The message input value
     */
    getMessageInput: function() {
        return document.getElementById('message-input').value.trim();
    },
    
    /**
     * Clear the message input field
     */
    clearMessageInput: function() {
        document.getElementById('message-input').value = '';
    },
    
    /**
     * Display the conversation list in the sidebar
     * @param {Array} conversations - List of conversation objects
     * @param {Function} loadCallback - Callback for loading a conversation
     * @param {Function} deleteCallback - Callback for deleting a conversation
     * @param {Function} clearAllCallback - Callback for clearing all conversations
     */
    displayConversationList: function(conversations, loadCallback, deleteCallback, clearAllCallback) {
        const conversationsList = document.getElementById('conversations-list');
        conversationsList.innerHTML = '';
        
        conversations.forEach(conv => {
            const convDiv = document.createElement('div');
            convDiv.className = 'conversation-item';
            
            // Create title span
            const titleSpan = document.createElement('span');
            titleSpan.textContent = conv.title;
            titleSpan.className = 'conversation-title';
            titleSpan.onclick = () => loadCallback(conv.conversation_id);
            
            // Create delete button
            const deleteButton = document.createElement('button');
            deleteButton.innerHTML = '&times;';
            deleteButton.className = 'delete-button';
            deleteButton.onclick = (e) => {
                e.stopPropagation(); // Prevent triggering the conversation loading
                deleteCallback(conv.conversation_id);
            };
            
            // Add both to the conversation item
            convDiv.appendChild(titleSpan);
            convDiv.appendChild(deleteButton);
            
            conversationsList.appendChild(convDiv);
        });
        
        // Add a "Clear All" button if there are conversations
        if (conversations.length > 0) {
            const clearAllButton = document.createElement('button');
            clearAllButton.textContent = 'Clear All Conversations';
            clearAllButton.className = 'clear-all-button';
            clearAllButton.onclick = clearAllCallback;
            conversationsList.appendChild(document.createElement('hr'));
            conversationsList.appendChild(clearAllButton);
        }
    }
};

export default UIController;