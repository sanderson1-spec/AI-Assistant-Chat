/**
 * Message formatting utilities for the chat application
 */

const MessageFormatter = {
    /**
     * Parse markdown syntax in text and convert to HTML
     * @param {string} text - The raw text to be parsed
     * @returns {string} HTML formatted text
     */
    parseMarkdown: function(text) {
        if (!text) return '';
        
        // Replace *text* with <em>text</em> for italics
        // The regex looks for text between asterisks, but not if the asterisk is:
        // - preceded by a backslash (escaped)
        // - part of a word (no space before/after)
        let formattedText = text.replace(/(?<!\\\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
        
        // Replace line breaks with <br> tags
        formattedText = formattedText.replace(/\n/g, '<br>');
        
        return formattedText;
    },
    
    /**
     * Format a message for display in the chat
     * @param {string} content - The message content
     * @param {string} role - The role (user/assistant)
     * @returns {HTMLElement} The formatted message element
     */
    formatMessage: function(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        // Apply markdown parsing and set as HTML
        messageDiv.innerHTML = this.parseMarkdown(content);
        
        return messageDiv;
    }
};

// Export the MessageFormatter object
export default MessageFormatter;