"""
Central Controller for AI Assistant
Orchestrates communication between user and specialized bots
"""
import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class CentralController:
    """Coordinates the AI Assistant system and delegates to specialized bots"""
    
    def __init__(self, database, bot_registry, task_scheduler, notification_service, llm_client=None):
        self.database = database
        self.bot_registry = bot_registry
        self.task_scheduler = task_scheduler
        self.notification_service = notification_service
        self.llm_client = llm_client  # LLM client for general conversation
        self.logger = logging.getLogger("ai-assistant.central-controller")
    
    async def process_message(self, user_id: str, message: str, conversation_id: Optional[str] = None):
        """
        Process an incoming message from the user
        
        Args:
            user_id: ID of the user
            message: Text message from the user
            conversation_id: ID of the conversation (optional)
            
        Returns:
            Response data including text and metadata
        """
        self.logger.info(f"Processing message from user {user_id}: {message[:50]}...")
        
        # If no conversation ID, create a new one
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
        
        # Attempt to analyze intent and identify capabilities
        try:
            if self.llm_client and hasattr(self.llm_client, 'analyze_intent'):
                capabilities = await self.llm_client.analyze_intent(message, context)
            else:
                capabilities = await self.analyze_message_intent(message, context)
        except Exception as e:
            self.logger.error(f"Error analyzing intent: {str(e)}")
            capabilities = ['assistant']
        
        # If no specific capabilities detected or only general assistant, use LLM
        if not capabilities or capabilities == ['assistant']:
            try:
                # Prepare message for LLM
                llm_messages = [
                    {"role": "user", "content": message}
                ]
                
                # Generate response from LLM with full context
                response = await self.llm_client.generate_response(llm_messages, context)
                
                # Store assistant response
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
                self.logger.error(f"Error using LLM for general conversation: {str(e)}", exc_info=True)
                
                # Fallback response if LLM fails
                fallback_response = "I'm having trouble understanding at the moment. Could you rephrase that?"
                
                # Store fallback response
                response_id, _ = await self.database.store_message(
                    user_id=user_id,
                    content=fallback_response,
                    role="assistant",
                    conversation_id=conversation_id,
                    parent_id=message_id
                )
                
                return {
                    "response": fallback_response,
                    "conversation_id": conversation_id,
                    "message_id": response_id,
                    "parent_id": message_id
                }
        
        # Collect responses from appropriate bots
        bot_responses = []
        scheduled_tasks = []
        scheduled_notifications = []
        context_updates = {}
        
        for capability in capabilities:
            # Get bots that can handle this capability
            bots = self.bot_registry.get_bots_for_capability(capability)
            
            # Skip if no bots can handle this capability
            if not bots:
                self.logger.warning(f"No bots available for capability: {capability}")
                continue
            
            # Use the highest priority bot for this capability
            bot = bots[0]
            self.logger.info(f"Selected bot '{bot.id}' for capability '{capability}'")
            
            # Process the message with this bot
            try:
                self.logger.info(f"Processing message with bot {bot.id}")
                response = await bot.process_message(user_id, message, context)
                self.logger.info(f"Bot {bot.id} response: {str(response)[:200]}...")
                
                # Collect response data
                if response.get("response"):
                    bot_responses.append({
                        "bot_id": bot.id,
                        "bot_name": bot.name,
                        "response": response["response"]
                    })
                
                # Collect scheduled tasks
                if response.get("scheduled_tasks"):
                    for task in response["scheduled_tasks"]:
                        scheduled_tasks.append({
                            "bot_id": bot.id,
                            **task
                        })
                
                # Collect scheduled notifications
                if response.get("scheduled_notifications"):
                    scheduled_notifications.extend(response["scheduled_notifications"])
                
                # Collect context updates
                if response.get("context_updates"):
                    context_updates.update(response["context_updates"])
                    
            except Exception as e:
                self.logger.error(f"Error processing message with bot {bot.id}: {str(e)}", exc_info=True)
                # Don't let one bot failure prevent others from processing
        
        # Combine responses from bots
        combined_response = self.combine_responses(bot_responses)
        
        # Store assistant response
        response_id, _ = await self.database.store_message(
            user_id=user_id,
            content=combined_response,
            role="assistant",
            conversation_id=conversation_id,
            parent_id=message_id
        )
        
        # Update conversation context
        if context_updates:
            await self.update_conversation_context(conversation_id, context_updates)
        
        # Schedule any tasks from the bots
        for task in scheduled_tasks:
            await self.task_scheduler.schedule_task(
                task_type=task["type"],
                bot_id=task["bot_id"],
                user_id=user_id,
                execute_at=task["execute_at"],
                params=task["params"],
                recurring=task.get("recurring", False),
                interval=task.get("interval")
            )
        
        # Schedule any notifications from the bots
        for notification in scheduled_notifications:
            if "send_at" in notification:
                # Future notification
                await self.notification_service.schedule_notification(
                    user_id=user_id,
                    message=notification["message"],
                    send_at=notification["send_at"],
                    source_bot_id=notification.get("source_bot_id"),
                    metadata=notification.get("metadata")
                )
            else:
                # Immediate notification
                await self.notification_service.send_notification(
                    user_id=user_id,
                    message=notification["message"],
                    source_bot_id=notification.get("source_bot_id"),
                    metadata=notification.get("metadata")
                )
        
        return {
            "response": combined_response,
            "conversation_id": conversation_id,
            "message_id": response_id,
            "parent_id": message_id
        }
    
    async def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get context for a conversation, including system time information
        
        Args:
            conversation_id: ID of the current conversation
        
        Returns:
            A dictionary with conversation context and current time information
        """
        # Get current date and time information
        now = datetime.now().astimezone()  # Get timezone-aware current time
        
        # Generate time-related context
        time_context = {
            "current_datetime": now.isoformat(),
            "current_date": now.date().isoformat(),
            "current_time": now.time().isoformat(),
            "current_day_of_week": now.strftime("%A"),
            "tomorrow_date": (now + timedelta(days=1)).date().isoformat(),
            "tomorrow_day_of_week": (now + timedelta(days=1)).strftime("%A"),
            "next_week_start": (now + timedelta(days=7-now.weekday())).date().isoformat(),
            "timezone": str(now.tzinfo)
        }
        
        # Get recent messages
        messages = await self.database.get_conversation_history(conversation_id, limit=10)
        
        # Get any stored context for this conversation
        stored_context = await self.database.get_conversation_context(conversation_id)
        
        # Combine into a complete context object
        context = {
            "messages": messages,
            "conversation_id": conversation_id,
            "timestamp": now.isoformat(),
            "time_context": time_context,
            **stored_context
        }
        
        return context
    
    async def analyze_message_intent(self, message: str, context: Dict[str, Any]) -> List[str]:
        """
        Fallback method to analyze message intent using keywords
        """
        # Fallback to a simple keyword-based approach
        capabilities = set()
        message_lower = message.lower()
        
        # Define keyword mappings for different capabilities
        capability_keywords = {
            "reminders": [
                "remind", "reminder", "schedule", "timer", "alarm", 
                "notify", "notification", "alert", "deadline"
            ],
            "todos": [
                "todo", "task", "to-do", "checklist", 
                "list", "add item", "mark complete", "finish task"
            ],
            "calendar": [
                "meeting", "appointment", "schedule", "event", 
                "book", "reservation", "availability", "date"
            ],
            "email": [
                "email", "mail", "send message", "draft", "compose"
            ],
            "search": [
                "find", "search", "lookup", "information about", 
                "tell me about", "what is", "who is"
            ]
        }
        
        # Check for keywords in the message
        for capability, keywords in capability_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                capabilities.add(capability)
                self.logger.info(f"Found keywords for capability: {capability}")
        
        # If no specific capabilities detected, use general assistant
        if not capabilities:
            capabilities.add("assistant")
            self.logger.info("No specific capabilities detected, defaulting to general assistant")
        
        return list(capabilities)
    
    def combine_responses(self, bot_responses: List[Dict[str, Any]]) -> str:
        """
        Combine responses from multiple bots into a coherent message
        
        Args:
            bot_responses: List of bot responses
            
        Returns:
            Combined response text
        """
        # If only one response, return it directly
        if len(bot_responses) == 1:
            return bot_responses[0]["response"]
        
        # Multiple responses - format nicely
        combined = ""
        for i, response in enumerate(bot_responses):
            # Only include bot name if multiple bots
            if len(bot_responses) > 1:
                combined += f"**{response['bot_name']}**:\n{response['response']}"
            else:
                combined += response["response"]
            
            # Add spacing between responses
            if i < len(bot_responses) - 1:
                combined += "\n\n"
        
        return combined
    
    async def update_conversation_context(self, conversation_id: str, updates: Dict[str, Any]):
        """Update context for a conversation"""
        await self.database.update_conversation_context(conversation_id, updates)