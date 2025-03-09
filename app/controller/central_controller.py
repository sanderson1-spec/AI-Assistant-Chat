"""
Central Controller for the AI Assistant
Coordinates character interactions and message handling
"""
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import json
import re
import asyncio
import uuid
import dateparser

from app.database.database import Database
from app.llm.lmstudio_client import LMStudioClient
from app.proactive.proactive_system import ProactiveSystem
from app.personality.personality_manager import PersonalityManager
from app.tasks.task_scheduler import TaskScheduler
from app.notifications.notification_service import NotificationService

class CentralController:
    """Coordinates the AI Assistant system with character-driven interactions"""
    
    def __init__(
        self,
        database: Database,
        personality_manager: PersonalityManager,
        task_scheduler: TaskScheduler,
        notification_service: NotificationService,
        llm_client: Optional[LMStudioClient] = None,
        websocket_manager = None  # Type hint omitted for circular import
    ):
        self.database = database
        self.personality_manager = personality_manager
        self.task_scheduler = task_scheduler
        self.notification_service = notification_service
        self.llm_client = llm_client
        self.logger = logging.getLogger("ai-assistant.controller")
        
        # Initialize proactive system
        self.proactive_system = ProactiveSystem(
            websocket_manager=websocket_manager,
            personality_manager=personality_manager,
            task_scheduler=task_scheduler
        )
        
        # Load Jess's character
        try:
            asyncio.create_task(self.personality_manager.load_character("jess"))
            self.logger.info("Loaded Jess's character")
        except Exception as e:
            self.logger.error(f"Error loading Jess's character: {str(e)}")
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process an incoming message using the character-driven approach"""
        try:
            # Store the message if it's not an edit (message_id is None)
            if message_id is None:
                message_id, conversation_id = await self.database.store_message(
                    user_id=user_id,
                    content=message,
                    role="user",
                    conversation_id=conversation_id
                )
            
            # Get conversation context
            context = await self.get_conversation_context(conversation_id)
            
            # Detect tasks in user's message
            self.logger.info("Attempting to detect tasks in user message...")
            user_tasks = await self.llm_client.detect_tasks(message)
            self.logger.info(f"Detected {len(user_tasks)} tasks in user message")
            
            # Store any tasks found in user's message
            for task in user_tasks:
                task_id = str(uuid.uuid4())
                self.logger.info(f"Processing task from user message: {task}")
                
                # Format task parameters
                task_params = {
                    "text": task["text"],
                    "user_id": user_id,
                    "conversation_id": conversation_id
                }
                self.logger.info(f"Task parameters: {task_params}")
                
                # Convert deadline string to datetime
                try:
                    deadline = dateparser.parse(task['deadline'], settings={'PREFER_DATES_FROM': 'future'})
                    if deadline:
                        task_params['deadline'] = deadline
                        try:
                            await self.task_scheduler.store_task(task_id, task_params)
                        except Exception as e:
                            self.logger.error(f"Error storing task {task_id}: {e}")
                    else:
                        self.logger.warning(f"Could not parse deadline: {task['deadline']}")
                except Exception as e:
                    self.logger.error(f"Error parsing deadline: {e}")
            
            # Build conversation history for response generation
            recent_messages = []
            
            if conversation_id:
                # Get last 5 messages for context
                history = await self.database.get_conversation_history(conversation_id, limit=5)
                for msg in history:
                    # Only include messages that are part of the conversation flow
                    if msg["role"] in ["user", "assistant"]:
                        recent_messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # Add current message
            recent_messages.append({"role": "user", "content": message})
            
            # Generate character response
            try:
                response = await self.llm_client.generate_response(
                    messages=recent_messages,
                    context=context
                )
                
                # Store response
                response_id, _ = await self.database.store_message(
                    user_id=user_id,
                    content=response,
                    role="assistant",
                    conversation_id=conversation_id,
                    parent_id=message_id
                )
                
                # Detect tasks in the response
                self.logger.info("Attempting to detect tasks in response...")
                response_tasks = await self.llm_client.detect_tasks(response)
                self.logger.info(f"Detected {len(response_tasks)} tasks in response")
                
                # Store any tasks found in response
                for task in response_tasks:
                    task_id = str(uuid.uuid4())
                    self.logger.info(f"Processing task from response: {task}")
                    
                    # Format task parameters
                    task_params = {
                        "text": task["text"],
                        "user_id": user_id,
                        "conversation_id": conversation_id
                    }
                    self.logger.info(f"Task parameters: {task_params}")
                    
                    # Convert deadline string to datetime
                    try:
                        deadline = dateparser.parse(task['deadline'], settings={'PREFER_DATES_FROM': 'future'})
                        if deadline:
                            task_params['deadline'] = deadline
                            try:
                                await self.task_scheduler.store_task(task_id, task_params)
                            except Exception as e:
                                self.logger.error(f"Error storing task {task_id}: {e}")
                        else:
                            self.logger.warning(f"Could not parse deadline: {task['deadline']}")
                    except Exception as e:
                        self.logger.error(f"Error parsing deadline: {e}")
                
                return {
                    "response": response,
                    "conversation_id": conversation_id,
                    "message_id": response_id,
                    "parent_id": message_id
                }
                
            except Exception as e:
                self.logger.error(f"Error generating response: {str(e)}", exc_info=True)
                raise  # Let the outer try-catch handle this
                
        except Exception as e:
            self.logger.error(f"Error processing interaction: {str(e)}", exc_info=True)
            raise
    
    async def _extract_time_patterns(self, message: str) -> List[Dict[str, Any]]:
        """Extract time-related patterns from message for scheduling follow-ups"""
        patterns = []
        
        # Common time patterns
        time_keywords = {
            r"in (\d+) (minute|minutes|min|mins)": lambda x: timedelta(minutes=int(x)),
            r"in (\d+) (hour|hours|hr|hrs)": lambda x: timedelta(hours=int(x)),
            r"at (\d{1,2}):(\d{2})": lambda h, m: self._next_time(int(h), int(m)),
            r"tomorrow at (\d{1,2}):(\d{2})": lambda h, m: self._next_time(int(h), int(m), tomorrow=True)
        }
        
        for pattern, time_func in time_keywords.items():
            matches = re.finditer(pattern, message.lower())
            for match in matches:
                try:
                    if len(match.groups()) == 1:
                        time = datetime.now() + time_func(match.group(1))
                    else:
                        time = time_func(*match.groups())
                    
                    patterns.append({
                        "time": time,
                        "context": match.group(0),
                        "original": match.group(0)
                    })
                except Exception as e:
                    self.logger.error(f"Error parsing time pattern: {str(e)}")
        
        return patterns
    
    def _next_time(self, hour: int, minute: int, tomorrow: bool = False) -> datetime:
        """Calculate the next occurrence of a specific time"""
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute)
        
        if tomorrow:
            target = target + timedelta(days=1)
        elif target <= now:
            target = target + timedelta(days=1)
        
        return target
    
    async def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get context for a conversation"""
        try:
            return await self.database.get_conversation_context(conversation_id)
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {str(e)}")
            return {}