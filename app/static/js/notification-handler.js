/**
 * Handle notifications in the UI
 */
import WebSocketManager from './websocket.js';

const NotificationHandler = {
    /**
     * Initialize notification container
     */
    init: function() {
        console.log('Initializing notification system');
        
        // Create notification container if it doesn't exist
        if (!document.querySelector('.notifications-container')) {
            const container = document.createElement('div');
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        
        // Create notification tray icon in corner
        if (!document.querySelector('.notifications-tray')) {
            const tray = document.createElement('div');
            tray.className = 'notifications-tray';
            tray.innerHTML = '<i class="notifications-icon">🔔</i><span class="count">0</span>';
            tray.addEventListener('click', this.toggleNotificationsPanel);
            document.body.appendChild(tray);
            
            // Hide count if 0
            this.updateNotificationCount(0);
        }
        
        // Fetch unread notifications on startup
        this.fetchUnreadNotifications();
    },
    
    /**
     * Handle an incoming notification
     * @param {Object} data - Notification data
     */
    handleNotification: function(data) {
        console.log('Received notification:', data);
        
        // Play notification sound if available
        this.playNotificationSound();
        
        // Create notification element
        const notificationElement = this.createNotificationElement(data);
        
        // Add to container
        const container = document.querySelector('.notifications-container');
        container.appendChild(notificationElement);
        
        // Update notification count
        this.updateNotificationCount(container.children.length);
        
        // Auto-dismiss after delay for non-critical notifications
        if (!data.metadata || !data.metadata.persistent) {
            setTimeout(() => {
                this.dismissNotification(notificationElement, data.id);
            }, 10000); // 10 seconds
        }
    },
    
    /**
     * Create a notification element
     * @param {Object} data - Notification data
     * @returns {HTMLElement} The notification element
     */
    createNotificationElement: function(data) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.setAttribute('data-notification-id', data.id);
        
        if (data.source_bot_id) {
            notification.setAttribute('data-source-bot', data.source_bot_id);
        }
        
        // Create content
        const content = document.createElement('div');
        content.className = 'notification-content';
        content.textContent = data.message;
        
        // Create timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'notification-timestamp';
        
        // Format date nicely
        const date = new Date(data.timestamp);
        timestamp.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Create close button
        const closeButton = document.createElement('button');
        closeButton.className = 'notification-close';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.dismissNotification(notification, data.id);
        });
        
        // Add action button if metadata contains action
        if (data.metadata && data.metadata.action) {
            const actionButton = document.createElement('button');
            actionButton.className = 'notification-action';
            actionButton.textContent = data.metadata.actionText || 'Action';
            actionButton.addEventListener('click', () => {
                // Execute action and dismiss
                if (typeof data.metadata.action === 'function') {
                    data.metadata.action();
                } else if (typeof data.metadata.action === 'string') {
                    // Simple actions like opening URLs
                    if (data.metadata.action.startsWith('http')) {
                        window.open(data.metadata.action, '_blank');
                    }
                }
                this.dismissNotification(notification, data.id);
            });
            notification.appendChild(actionButton);
        }
        
        // Add elements to notification
        notification.appendChild(closeButton);
        notification.appendChild(content);
        notification.appendChild(timestamp);
        
        // Make the notification clickable to mark as read
        notification.addEventListener('click', () => {
            this.dismissNotification(notification, data.id);
        });
        
        return notification;
    },
    
    /**
     * Dismiss a notification
     * @param {HTMLElement} element - The notification element
     * @param {number} id - The notification ID
     */
    dismissNotification: function(element, id) {
        // Add fade-out animation
        element.style.opacity = '0';
        element.style.transform = 'translateX(100%)';
        element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        
        // Remove after animation
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
                
                // Update notification count
                const container = document.querySelector('.notifications-container');
                this.updateNotificationCount(container.children.length);
            }
        }, 300);
        
        // Mark as read on server
        this.markNotificationRead(id);
    },
    
    /**
     * Mark a notification as read
     * @param {number} notificationId - The notification ID
     */
    markNotificationRead: function(notificationId) {
        // If using websocket, send a notification_read message
        if (WebSocketManager && WebSocketManager.isConnected()) {
            WebSocketManager.sendMessage({
                type: 'notification_read',
                notification_id: notificationId
            });
        } else {
            // Fallback to REST API
            fetch(`/api/notifications/${notificationId}/read`, {
                method: 'POST'
            }).catch(error => {
                console.error('Error marking notification as read:', error);
            });
        }
    },
    
    /**
     * Update the notification count badge
     * @param {number} count - The number of notifications
     */
    updateNotificationCount: function(count) {
        const countElement = document.querySelector('.notifications-tray .count');
        if (countElement) {
            countElement.textContent = count;
            
            // Show/hide based on count
            if (count > 0) {
                countElement.style.display = 'flex';
            } else {
                countElement.style.display = 'none';
            }
        }
    },
    
    /**
     * Fetch unread notifications from the server
     */
    fetchUnreadNotifications: function() {
        const userId = WebSocketManager ? WebSocketManager.getUserId() : 'default_user';
        
        fetch(`/api/notifications?user_id=${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.notifications && data.notifications.length > 0) {
                    console.log(`Received ${data.notifications.length} unread notifications`);
                    data.notifications.forEach(notification => {
                        this.handleNotification(notification);
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching notifications:', error);
            });
    },
    
    /**
     * Toggle the notifications panel
     */
    toggleNotificationsPanel: function() {
        const container = document.querySelector('.notifications-container');
        
        if (container.style.display === 'none' || !container.style.display) {
            container.style.display = 'flex';
        } else {
            container.style.display = 'none';
        }
    },
    
    /**
     * Play a notification sound
     */
    playNotificationSound: function() {
        // Check if notification sounds are enabled
        const soundsEnabled = localStorage.getItem('notification_sounds') !== 'disabled';
        
        if (soundsEnabled) {
            // Create audio element if not exists
            let audio = document.getElementById('notification-sound');
            
            if (!audio) {
                audio = document.createElement('audio');
                audio.id = 'notification-sound';
                audio.src = '/static/sounds/notification.mp3'; // Default sound
                audio.volume = 0.5;
                document.body.appendChild(audio);
            }
            
            // Play sound
            audio.currentTime = 0;
            audio.play().catch(e => {
                console.log('Could not play notification sound:', e);
            });
        }
    },
    
    /**
     * Show a notification programmatically from another part of the app
     * @param {Object} notification - Notification data
     */
    showNotification: function(notification) {
        this.handleNotification({
            id: 'local-' + Date.now(),
            message: notification.message,
            timestamp: new Date().toISOString(),
            source_bot_id: notification.source_bot_id || 'system',
            metadata: notification.metadata || {}
        });
    }
};

// Initialize when loaded
document.addEventListener('DOMContentLoaded', () => {
    NotificationHandler.init();
});

export default NotificationHandler;