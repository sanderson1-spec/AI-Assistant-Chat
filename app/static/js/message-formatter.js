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
        
        // Escape HTML first to prevent XSS
        let formattedText = this.escapeHTML(text);
        
        // Replace *text* with <em>text</em> for italics
        formattedText = formattedText.replace(/(?<!\\\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
        
        // Replace **text** with <strong>text</strong> for bold
        formattedText = formattedText.replace(/(?<!\\\*)\*\*([^*]+)\*\*(?!\*)/g, '<strong>$1</strong>');
        
        // Replace `code` with <code>code</code> for inline code
        formattedText = formattedText.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Replace line breaks with <br> tags
        formattedText = formattedText.replace(/\n/g, '<br>');
        
        return formattedText;
    },
    
    /**
     * Escape HTML special characters to prevent XSS
     * @param {string} str - The string to escape
     * @returns {string} Escaped string
     */
    escapeHTML: function(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },
    
    /**
     * Format a string as plain text (no markdown)
     * @param {string} text - The text to format
     * @returns {string} Formatted text
     */
    formatPlainText: function(text) {
        if (!text) return '';
        
        // Escape HTML and replace line breaks
        return this.escapeHTML(text).replace(/\n/g, '<br>');
    }
};

// Export the MessageFormatter object
export default MessageFormatter;