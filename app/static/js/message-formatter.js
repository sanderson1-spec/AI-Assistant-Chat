/**
 * message-formatter.js - Handles formatting of chat messages
 */

/**
 * Convert text with simple Markdown syntax to HTML
 * @param {string} text - Text to format with markdown
 * @returns {string} - HTML formatted text
 */
function formatMarkdown(text) {
    if (!text) return '';
    
    // Clone the text to avoid modifying the original
    let formattedText = String(text);
    
    // Replace *text* with <em>text</em> (italic)
    // Use a lookahead and lookbehind to ensure we don't match within words
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
 * Format a timestamp for display
 * @param {Date|string} timestamp - Date object or ISO string
 * @param {boolean} includeEdited - Whether to include "(edited)" text
 * @returns {string} - Formatted time string
 */
function formatTimestamp(timestamp, includeEdited = false) {
    let date;
    
    if (typeof timestamp === 'string') {
        date = new Date(timestamp);
    } else if (timestamp instanceof Date) {
        date = timestamp;
    } else {
        date = new Date();
    }
    
    const timeString = date.toLocaleTimeString();
    return includeEdited ? `${timeString} (edited)` : timeString;
}

// Export formatters for use in other modules
window.messageFormatter = {
    formatMarkdown,
    formatTimestamp
};