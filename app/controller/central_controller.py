"""
Central Controller for the AI Assistant
Coordinates character interactions and message handling
"""
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
import json
import re

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
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an incoming message using the character-driven approach"""
        self.logger.info(f"Processing message from user {user_id}: {message[:50]}...")
        
        # Create or get conversation
        if not conversation_id:
            conversation_id = f"conv_{datetime.now().isoformat()}_{user_id}"
            await self.database.create_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                title=f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        
        # Store user message
        message_id, _ = await self.database.store_message(
            user_id=user_id,
            content=message,
            role="user",
            conversation_id=conversation_id
        )
        
        # Get conversation context
        context = await self.get_conversation_context(conversation_id)
        
        try:
            # Process message through personality system
            if self.llm_client:
                # Check for time-related patterns in message
                time_patterns = await self._extract_time_patterns(message)
                if time_patterns:
                    # Schedule follow-ups for any detected times
                    for pattern in time_patterns:
                        await self.proactive_system.schedule_followup(
                            scheduled_time=pattern["time"],
                            context={
                                "original_message": message,
                                "detected_time": pattern["time"].isoformat(),
                                "time_context": pattern["context"]
                            },
                            user_id=user_id
                        )
                
                # Generate character response
                response = await self.llm_client.generate_response(
                    messages=[{"role": "user", "content": message}],
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
                
                return {
                    "response": response,
                    "conversation_id": conversation_id,
                    "message_id": response_id,
                    "parent_id": message_id
                }
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}", exc_info=True)
            
            # Fallback response
            fallback = "I'm having trouble processing that right now. Could you rephrase?"
            response_id, _ = await self.database.store_message(
                user_id=user_id,
                content=fallback,
                role="assistant",
                conversation_id=conversation_id,
                parent_id=message_id
            )
            
            return {
                "response": fallback,
                "conversation_id": conversation_id,
                "message_id": response_id,
                "parent_id": message_id
            }
    
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