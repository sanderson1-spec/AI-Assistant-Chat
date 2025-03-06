/**
 * utils.js - Utility functions for the chat application
 */

/**
 * Display debug messages in the console and optionally in the UI
 * @param {string} message - Debug message to display
 * @param {boolean} isError - Whether this is an error message
 */
function showDebugMessage(message, isError = false) {
    console.log(message);
    // Optionally display in the UI for better visibility
    const chatContainer = document.getElementById('chat-container');
    if (!chatContainer) return;
    
    const debugDiv = document.createElement('div');
    debugDiv.className = `debug-message ${isError ? 'error' : 'info'}`;
    debugDiv.textContent = `[Debug] ${message}`;
    chatContainer.appendChild(debugDiv);
}

/**
 * Find an element by ID with error handling
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} - The DOM element or null if not found
 */
function getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        showDebugMessage(`Element with ID '${id}' not found`, true);
    }
    return element;
}

/**
 * Safely parse JSON with error handling
 * @param {string} jsonString - The JSON string to parse
 * @returns {object|null} - Parsed object or null on error
 */
function safeJsonParse(jsonString) {
    try {
        return JSON.parse(jsonString);
    } catch (error) {
        showDebugMessage(`Error parsing JSON: ${error.message}`, true);
        return null;
    }
}

/**
 * Generate a unique ID for messages
 * @returns {string} - Unique ID
 */
function generateId() {
    return Date.now().toString();
}

// Export utilities for use in other modules
window.chatUtils = {
    showDebugMessage,
    getElement,
    safeJsonParse,
    generateId
};