/**
 * Utility functions for the chat application
 */

const Utils = {
    /**
     * Generate a random client ID
     * @returns {string} A random string ID
     */
    generateClientId: function() {
        return Math.random().toString(36).substring(2, 15);
    },
    
    /**
     * Format a date for display
     * @param {string} dateString - ISO format date string
     * @returns {string} Formatted date string
     */
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString();
    },
    
    /**
     * Truncate a string to a maximum length
     * @param {string} str - The string to truncate
     * @param {number} maxLength - Maximum length
     * @returns {string} Truncated string
     */
    truncateString: function(str, maxLength = 30) {
        if (str.length <= maxLength) return str;
        return str.substring(0, maxLength) + '...';
    },
    
    /**
     * Escape HTML special characters to prevent XSS
     * Note: This is a basic implementation. For production, consider using a library
     * @param {string} str - The string to escape
     * @returns {string} Escaped string
     */
    escapeHTML: function(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};

export default Utils;