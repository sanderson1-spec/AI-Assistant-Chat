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
            console.log('Created notifications container');
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
            console.log('Created notifications tray');
        }
        
        // Ensure styles are loaded
        this.ensureNotificationStyles();
        
        // Fetch unread notifications on startup
        this.fetchUnreadNotifications();
        
        console.log('Notification system initialized');
    },
    
    /**
     * Ensure notification styles are in the document
     */
    ensureNotificationStyles: function() {
        // Check if styles are already loaded
        const styleElement = document.getElementById('notification-styles');
        if (styleElement) return;
        
        // Create style element
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
        /* Notification System Styles */
        .notifications-container {
            position: fixed;
            top: 20px;
            right: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 320px;
            z-index: 1000;
        }
        
        .notification {
            background-color: white;
            border-left: 4px solid #4285f4;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 12px 15px;
            margin-bottom: 10px;
            width: 100%;
            position: relative;
            animation: slide-in 0.3s ease-out;
            cursor: pointer;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }
        
        .notification:hover {
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }
        
        /* Different colors based on the source bot */
        .notification[data-source-bot="reminder_bot"] {
            border-left-color: #ff9800;
        }
        
        .notification[data-source-bot="todo_bot"] {
            border-left-color: #4caf50;
        }
        
        .notification[data-source-bot="calendar_bot"] {
            border-left-color: #9c27b0;
        }
        
        .notification[data-source-bot="email_bot"] {
            border-left-color: #f44336;
        }
        
        .notification[data-source-bot="notification_service"] {
            border-left-color: #4285f4;
        }
        
        /* Notification content */
        .notification-content {
            margin-bottom: 8px;
            padding-right: 20px;
        }
        
        /* Timestamp */
        .notification-timestamp {
            font-size: 11px;
            color: #888;
            margin-top: 5px;
        }
        
        /* Close button */
        .notification-close {
            position: absolute;
            top: 5px;
            right: 5px;
            background: none;
            border: none;
            color: #aaa;
            font-size: 16px;
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 50%;
        }
        
        .notification-close:hover {
            background-color: #f0f0f0;
            color: #666;
        }
        
        /* Action button for actionable notifications */
        .notification-action {
            background-color: #f0f0f0;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 12px;
            cursor: pointer;
            margin-top: 5px;
        }
        
        .notification-action:hover {
            background-color: #e3e3e3;
        }
        
        /* Slide-in animation */
        @keyframes slide-in {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        /* Minimized notifications tray */
        .notifications-tray {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #4285f4;
            color: white;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1000;
        }
        
        .notifications-tray:hover {
            background-color: #3367d6;
        }
        
        .notifications-tray .count {
            position: absolute;
            top: -5px;
            right: -5px;
            background-color: #f44336;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        `;
        
        document.head.appendChild(style);
        console.log('Added notification styles to document');
    },
    
    /**
     * Handle an incoming notification
     * @param {Object} data - Notification data
     */
    handleNotification: function(data) {
        console.log('Handling notification:', data);
        
        // Play notification sound if available
        this.playNotificationSound();
        
        // Create notification element
        const notificationElement = this.createNotificationElement(data);
        
        // Add to container - ensure container exists first
        let container = document.querySelector('.notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notifications-container';
            document.body.appendChild(container);
            console.log('Created notifications container on-demand');
        }
        
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
                this.updateNotificationCount(container ? container.children.length : 0);
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
        
        if (container) {
            if (container.style.display === 'none' || !container.style.display) {
                container.style.display = 'flex';
            } else {
                container.style.display = 'none';
            }
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

export default NotificationHandler;