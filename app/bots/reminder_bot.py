"""
ReminderBot - A specialized bot for setting and managing reminders
"""
import re
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional

try:
    import dateparser
except ImportError:
    print("Warning: dateparser package not installed. ReminderBot will have limited date parsing capabilities.")
    # Fallback implementation if dateparser is not available
    dateparser = None

from app.bots.bot_framework import BaseBot, BotCapability

logger = logging.getLogger("ai-assistant.reminder-bot")

class ReminderBot(BaseBot):
    """Bot for setting and managing time-based reminders"""
    
    def __init__(self):
        super().__init__(
            bot_id="reminder_bot",
            name="Reminder Assistant",
            description="I can help you set reminders and follow up at specific times."
        )
        
        # Register capabilities
        self.register_capability(BotCapability(
            name="reminders",
            description="Set and manage reminders",
            keywords=["remind", "reminder", "schedule", "timer", "alarm", "notification", "notify"],
            priority=10  # High priority for reminder tasks
        ))
        
        # Register task types
        self.register_task_type("reminder_notification")
    
    async def process_message(self, user_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process messages related to reminders"""
        # Extract reminder details from message
        reminder_info = self.extract_reminder_info(message)
        
        # Handle different reminder intents
        if reminder_info.get("action") == "set":
            return await self.handle_set_reminder(user_id, reminder_info)
            
        elif reminder_info.get("action") == "list":
            return await self.handle_list_reminders(user_id)
            
        elif reminder_info.get("action") == "cancel":
            return await self.handle_cancel_reminder(user_id, reminder_info)
            
        else:
            # Couldn't determine specific intent - offer help
            return {
                "response": "I can help you set reminders. Try saying something like:\n"
                            "• Remind me to check email in 5 minutes\n"
                            "• Set a reminder for my meeting tomorrow at 2pm\n"
                            "• List my reminders\n"
                            "• Cancel my reminder about the email"
            }
    
    async def execute_task(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute reminder tasks"""
        if task_type == "reminder_notification":
            user_id = params.get("user_id")
            reminder_text = params.get("text", "")
            
            # Prepare notification for user
            return {
                "success": True,
                "notifications": [{
                    "message": f"⏰ Reminder: {reminder_text}",
                    "metadata": {"type": "reminder"}
                }]
            }
        
        return {"success": False, "error": "Unknown task type"}
    
    async def handle_set_reminder(self, user_id: str, reminder_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle setting a new reminder"""
        reminder_text = reminder_info.get("text", "").strip()
        reminder_time = reminder_info.get("time")
        
        if not reminder_text or not reminder_time:
            return {
                "response": "I need both what to remind you about and when. For example, 'Remind me to check email in 5 minutes.'"
            }
        
        # Format time for display
        time_str = reminder_time.strftime("%I:%M %p")
        date_str = reminder_time.strftime("%A, %B %d")
        
        # If same day, just show time
        if reminder_time.date() == datetime.now().date():
            display_time = f"today at {time_str}"
        # If tomorrow, say tomorrow
        elif reminder_time.date() == (datetime.now() + timedelta(days=1)).date():
            display_time = f"tomorrow at {time_str}"
        else:
            display_time = f"on {date_str} at {time_str}"
        
        # Calculate time difference for immediate feedback
        time_diff = reminder_time - datetime.now()
        minutes = time_diff.total_seconds() / 60
        
        if minutes < 1:
            time_feedback = "in less than a minute"
        elif minutes < 60:
            time_feedback = f"in about {int(minutes)} minute{'s' if minutes != 1 else ''}"
        elif minutes < 60 * 24:
            hours = minutes / 60
            time_feedback = f"in about {int(hours)} hour{'s' if hours != 1 else ''}"
        else:
            days = minutes / (60 * 24)
            time_feedback = f"in about {int(days)} day{'s' if days != 1 else ''}"
        
        # Schedule the reminder notification
        return {
            "response": f"I'll remind you to '{reminder_text}' {display_time} ({time_feedback}).",
            "scheduled_notifications": [{
                "message": f"⏰ Reminder: {reminder_text}",
                "send_at": reminder_time,
                "metadata": {"type": "reminder", "text": reminder_text}
            }]
        }
    
    async def handle_list_reminders(self, user_id: str) -> Dict[str, Any]:
        """Handle listing all reminders"""
        # In a real implementation, we would fetch from the database
        # For this example, we'll return a placeholder
        
        return {
            "response": "You don't have any active reminders. You can set one by saying 'Remind me to...'."
        }
    
    async def handle_cancel_reminder(self, user_id: str, reminder_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle canceling a reminder"""
        # In a real implementation, we would cancel in the database
        # For this example, we'll return a placeholder
        
        return {
            "response": "I don't see any active reminders matching that description. You can say 'List my reminders' to see what's scheduled."
        }
    
    def extract_reminder_info(self, message: str) -> Dict[str, Any]:
        """
        Extract reminder details from message text
        
        Returns:
            Dictionary with keys:
            - action: 'set', 'list', or 'cancel'
            - text: The reminder text (what to remind about)
            - time: Datetime object of when to remind
        """
        message = message.lower()
        result = {}
        
        # Check for list reminders intent
        if re.search(r'(list|show|what|any)\s+(reminders|reminder)', message):
            result["action"] = "list"
            return result
        
        # Check for cancel reminder intent
        if re.search(r'(cancel|delete|remove)\s+(reminder|reminders)', message):
            result["action"] = "cancel"
            # Try to extract which reminder to cancel
            match = re.search(r'(cancel|delete|remove)\s+(?:my|the)?\s*reminder\s+(?:about|for|to)?\s*(.+)', message)
            if match:
                result["text"] = match.group(2).strip()
            return result
        
        # Check for set reminder intent
        remind_match = re.search(r'remind\s+(?:me)?\s+(?:to|about)?\s*(.+)', message)
        set_match = re.search(r'set\s+(?:a|an)?\s*reminder\s+(?:to|about|for)?\s*(.+)', message)
        
        if remind_match or set_match:
            result["action"] = "set"
            
            # Extract reminder text and time
            if remind_match:
                full_text = remind_match.group(1).strip()
            else:
                full_text = set_match.group(1).strip()
            
            # Try to find time indicators in the text
            time_match = None
            
            # Check for "in X minutes/hours"
            in_match = re.search(r'in\s+(\d+)\s+(minute|minutes|min|mins|hour|hours|hr|hrs)', full_text)
            if in_match:
                amount = int(in_match.group(1))
                unit = in_match.group(2)
                
                if unit.startswith('minute') or unit.startswith('min'):
                    result["time"] = datetime.now() + timedelta(minutes=amount)
                elif unit.startswith('hour') or unit.startswith('hr'):
                    result["time"] = datetime.now() + timedelta(hours=amount)
                
                # Remove time info from the reminder text
                result["text"] = re.sub(r'in\s+\d+\s+(minute|minutes|min|mins|hour|hours|hr|hrs)', '', full_text).strip()
                
            # Check for "at X time"
            elif "at " in full_text:
                parts = full_text.split("at ")
                result["text"] = parts[0].strip()
                time_str = parts[1].strip()
                
                # Parse the time using dateparser or fallback
                if dateparser:
                    parsed_time = dateparser.parse(time_str)
                    if parsed_time:
                        result["time"] = parsed_time
                else:
                    # Simple fallback for "today at X" or "tomorrow at X"
                    if ":" in time_str:
                        try:
                            hour, minute = map(int, time_str.split(":"))
                            now = datetime.now()
                            result["time"] = datetime(now.year, now.month, now.day, hour, minute)
                        except ValueError:
                            pass
            
            # Check for "tomorrow", "next week", etc.
            elif any(term in full_text for term in ["tomorrow", "next week", "next month", "tonight"]):
                # Use dateparser to handle these relative times
                if dateparser:
                    for term in ["tomorrow", "next week", "next month", "tonight"]:
                        if term in full_text:
                            # Remove the time term from the reminder text
                            result["text"] = full_text.replace(term, "").strip()
                            parsed_time = dateparser.parse(term)
                            if parsed_time:
                                result["time"] = parsed_time
                            break
                else:
                    # Simple fallback
                    if "tomorrow" in full_text:
                        now = datetime.now()
                        result["time"] = now + timedelta(days=1)
                        result["text"] = full_text.replace("tomorrow", "").strip()
            
            # If no specific time was found, try dateparser on the whole string
            if "time" not in result and dateparser:
                parsed_time = dateparser.parse(full_text, settings={'PREFER_DATES_FROM': 'future'})
                if parsed_time:
                    # Try to extract just the reminder text without the time
                    for time_phrase in [
                        "today", "tomorrow", "tonight", "next week", "next month", 
                        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
                    ]:
                        if time_phrase in full_text.lower():
                            parts = re.split(f"\\b{time_phrase}\\b", full_text, flags=re.IGNORECASE)
                            if len(parts) > 1:
                                result["text"] = parts[0].strip()
                                result["time"] = parsed_time
                                break
                
                # If we still don't have a clear text/time split, use the whole thing as text
                # and set a default time
                if "text" not in result:
                    result["text"] = full_text
                    result["time"] = datetime.now() + timedelta(minutes=30)  # Default 30 min
                
            # If we still don't have a time, default to 30 minutes from now
            if "time" not in result:
                result["time"] = datetime.now() + timedelta(minutes=30)
        
        return result