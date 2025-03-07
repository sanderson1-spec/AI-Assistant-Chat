/**
 * UI updates and DOM manipulation
 */

const UIController = {
    currentEditTextarea: null,
    
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
        document.getElementById('message-input').focus();
    },
    
    /**
     * Set the input focus to a specific textarea during editing
     * @param {HTMLTextAreaElement|null} textarea - The textarea to focus
     */
    setCurrentEditTextarea: function(textarea) {
        this.currentEditTextarea = textarea;
    },
    
    /**
     * Get the currently active textarea (message input or edit textarea)
     * @returns {HTMLElement|null} The active textarea
     */
    getCurrentTextInput: function() {
        return this.currentEditTextarea || document.getElementById('message-input');
    },
    
    /**
     * Set the message input to a textarea for multiline support
     */
    setupTextareaInput: function() {
        // Replace the input field with a textarea
        const inputContainer = document.querySelector('.input-container');
        const oldInput = document.getElementById('message-input');
        
        if (oldInput && oldInput.tagName !== 'TEXTAREA') {
            const currentValue = oldInput.value;
            
            // Create a new textarea
            const textarea = document.createElement('textarea');
            textarea.id = 'message-input';
            textarea.placeholder = "Type your message here...";
            textarea.value = currentValue;
            textarea.classList.add('message-textarea');
            
            // Replace the input with the textarea
            inputContainer.replaceChild(textarea, oldInput);
            
            // Add event listener for Shift+Enter
            textarea.addEventListener('keydown', (event) => {
                // Only Enter without shift sends the message
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    document.getElementById('send-button').click();
                }
            });
        }
    },
    
    /**
     * Add keyboard shortcut info to the UI
     */
    addKeyboardShortcutInfo: function() {
        const inputContainer = document.querySelector('.input-container');
        
        // Check if info already exists
        if (!document.querySelector('.key-binding-info')) {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'key-binding-info';
            infoDiv.textContent = 'Press Enter to send. Shift+Enter for new line. Cmd+R to regenerate last response.';
            
            // Add after the input container
            inputContainer.parentNode.insertBefore(infoDiv, inputContainer.nextSibling);
        }
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