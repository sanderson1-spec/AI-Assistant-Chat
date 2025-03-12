"""
Script Bot for delivering pre-planned messages
Part of the AI Assistant's script generation feature
"""
from datetime import datetime
import logging
import json
from typing import Dict, Any

from app.bots.bot_framework import BaseBot, BotCapability

class ScriptBot(BaseBot):
    """Bot that delivers pre-planned messages from scripts"""
    
    def __init__(self, bot_registry, websocket_manager, script_generator_system):
        """Initialize the script bot with dependencies"""
        super().__init__(
            bot_id="script_bot",
            name="Script Bot",
            description="Delivers pre-planned message scripts"
        )
        self.bot_registry = bot_registry
        self.websocket_manager = websocket_manager
        self.script_generator_system = script_generator_system
        self.logger = logging.getLogger("ai-assistant.script-bot")
        
        # Register capabilities
        self.register_capability(BotCapability(
            name="deliver_messages",
            description="Deliver pre-planned script messages",
            keywords=["script", "deliver", "message"],
            priority=5
        ))
        
        self.register_capability(BotCapability(
            name="execute_tasks",
            description="Execute scheduled script tasks",
            keywords=["script", "task", "execute"],
            priority=5
        ))
        
        # Register task types
        self.register_task_type("deliver_script_message")
    
    async def process_message(self, user_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user messages - Script bot doesn't handle direct messages"""
        # Script bot doesn't process direct messages, it only delivers scheduled scripts
        return {"response": None}
    
    async def execute_task(self, task_type: str, params: Dict[str, Any]) -> bool:
        """Execute a scheduled task for this bot"""
        try:
            if task_type == "deliver_script_message":
                return await self._deliver_script_message(params)
            else:
                self.logger.warning(f"Unknown task type: {task_type}")
                return False
        except Exception as e:
            self.logger.error(f"Error executing task {task_type}: {str(e)}", exc_info=True)
            return False
    
    async def _deliver_script_message(self, params: Dict[str, Any]) -> bool:
        """Deliver a script message to the user"""
        try:
            # Extract parameters
            script_id = params.get("script_id")
            message_id = params.get("message_id")
            user_id = params.get("user_id", "default_user")
            content = params.get("content", "")
            character_name = params.get("character_name", "AI Assistant")
            
            if not all([script_id, message_id, content]):
                self.logger.warning(f"Missing required parameters for script message delivery: {params}")
                return False
            
            # Get client IDs for the user
            client_ids = self.websocket_manager.get_client_ids_for_user(user_id)
            
            if not client_ids:
                self.logger.warning(f"No active connections for user {user_id}")
                # Still mark as delivered since we tried
                await self.script_generator_system.handle_script_message_delivered(script_id, message_id)
                return False
            
            # Format message
            # Extract message content from various possible field names
            MESSAGE_FIELDS = ['message', 'text', 'prompt', 'content', 'response']
            
            # Function to recursively extract message content
            def extract_message(content_obj):
                if isinstance(content_obj, str):
                    # Try to detect if this is a JSON string and parse it
                    content_str = content_obj.strip()
                    if (content_str.startswith('{') and content_str.endswith('}')) or \
                       (content_str.startswith('[') and content_str.endswith(']')):
                        try:
                            # Replace single quotes with double quotes for valid JSON
                            fixed_str = content_str.replace("'", '"')
                            parsed = json.loads(fixed_str)
                            return extract_message(parsed)
                        except:
                            pass
                    return content_str
                
                if isinstance(content_obj, dict):
                    # Try to find content in any of the common message fields
                    for field in MESSAGE_FIELDS:
                        if field in content_obj:
                            return extract_message(content_obj[field])
                    
                    # If there's only one value in the dict, use that
                    if len(content_obj) == 1:
                        return extract_message(list(content_obj.values())[0])
                    
                    # Otherwise, serialize to string and strip braces
                    json_str = json.dumps(content_obj)
                    # Remove the surrounding braces
                    if json_str.startswith('{') and json_str.endswith('}'):
                        inner_content = json_str[1:-1].strip()
                        # If it looks like "key": "value", extract just the value
                        if inner_content.count(':') == 1 and inner_content.count('"') >= 4:
                            parts = inner_content.split(':', 1)
                            if len(parts) == 2:
                                value_part = parts[1].strip()
                                if value_part.startswith('"') and value_part.endswith('"'):
                                    return value_part[1:-1]
                    return json_str
                
                if isinstance(content_obj, (list, tuple)):
                    # If it's a list with one item, use that
                    if len(content_obj) == 1:
                        return extract_message(content_obj[0])
                    return json.dumps(content_obj)
                
                # Default case, convert to string
                return str(content_obj)
            
            # Extract the actual message content
            content = extract_message(content)
                
            message_data = {
                "type": "script_message",
                "content": content,
                "script_id": script_id,
                "message_id": message_id,
                "character_name": character_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to all user connections
            success = False
            for client_id in client_ids:
                try:
                    await self.websocket_manager.send_message(client_id, message_data)
                    success = True
                except Exception as e:
                    self.logger.error(f"Error sending to client {client_id}: {str(e)}")
            
            # Mark message as delivered in script system
            if success:
                await self.script_generator_system.handle_script_message_delivered(script_id, message_id)
                self.logger.info(f"Delivered script message {message_id} for script {script_id}")
                return True
            else:
                self.logger.warning(f"Failed to deliver script message {message_id} for script {script_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error delivering script message: {str(e)}", exc_info=True)
            return False
    
    async def register(self):
        """Register this bot with the bot registry"""
        try:
            if self.bot_registry:
                self.bot_registry.register_bot(self)
                self.logger.info(f"Registered {self.name} with bot registry")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error registering {self.name}: {str(e)}", exc_info=True)
            return False 