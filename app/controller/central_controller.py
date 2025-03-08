"""
Central Controller for AI Assistant
Orchestrates communication between user and specialized bots
"""
import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

class CentralController:
    """Coordinates the AI Assistant system and delegates to specialized bots"""
    
    def __init__(self, database, bot_registry, task_scheduler, notification_service, llm_client=None):
        self.database = database
        self.bot_registry = bot_registry
        self.task_scheduler = task_scheduler
        self.notification_service = notification_service
        self.llm_client = llm_client  # Optional LLM client for intent analysis
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
        
        # Analyze intent to determine which bots should process the message
        capabilities = await self.analyze_message_intent(message, context)
        self.logger.info(f"Detected capabilities: {capabilities}")
        
        # Debug available bots
        all_bots = self.bot_registry.get_all_bots()
        self.logger.info(f"Available bots: {[bot.id for bot in all_bots]}")
        for bot in all_bots:
            self.logger.info(f"Bot {bot.id} capabilities: {[cap.name for cap in bot.capabilities]}")
        
        # Collect responses from appropriate bots
        bot_responses = []
        scheduled_tasks = []
        scheduled_notifications = []
        context_updates = {}
        
        for capability in capabilities:
            # Get bots that can handle this capability
            bots = self.bot_registry.get_bots_for_capability(capability)
            self.logger.info(f"Bots for capability '{capability}': {[bot.id for bot in bots]}")
            
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
        
        # If no bot could handle the message, use fallback response
        if not bot_responses:
            self.logger.warning("No bot responses generated, using fallback")
            bot_responses.append({
                "bot_id": "central_controller",
                "bot_name": "Assistant",
                "response": "I'm not sure how to help with that. Could you please rephrase your request?"
            })
        
        # Combine responses from all bots
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
    
    async def analyze_message_intent(self, message: str, context: Dict[str, Any]) -> List[str]:
        """
        Analyze message to determine capabilities needed to respond
        
        Args:
            message: Text message from the user
            context: Conversation context
            
        Returns:
            List of capability names that might handle this message
        """
        # Attempt to use LLM for intent detection if available
        if self.llm_client and hasattr(self.llm_client, "analyze_intent"):
            try:
                capabilities = await self.llm_client.analyze_intent(message, context)
                if capabilities:
                    self.logger.info(f"LLM detected intents: {capabilities}")
                    return capabilities
            except Exception as e:
                self.logger.error(f"Error using LLM for intent analysis: {str(e)}")
        
        # Fallback to keyword-based approach
        capabilities = set()
        message_lower = message.lower()
        
        # Check for time-related keywords (reminder bot)
        if any(keyword in message_lower for keyword in [
            "remind", "reminder", "schedule", "timer", "alarm", "in 5 minutes", 
            "tomorrow", "later", "notification", "alert me", "notify"
        ]):
            capabilities.add("reminders")
        
        # Check for todo-related keywords
        if any(keyword in message_lower for keyword in [
            "todo", "task", "list", "add item", "mark complete", "finish",
            "to-do", "to do", "checklist", "complete", "add a task"
        ]):
            capabilities.add("todos")
        
        # Check for calendar-related keywords
        if any(keyword in message_lower for keyword in [
            "calendar", "meeting", "appointment", "schedule", "event",
            "book", "reservation", "availability"
        ]):
            capabilities.add("calendar")
        
        # Check for email-related keywords
        if any(keyword in message_lower for keyword in [
            "email", "mail", "send", "draft", "compose", "write"
        ]):
            capabilities.add("email")
        
        # Check for search-related keywords
        if any(keyword in message_lower for keyword in [
            "search", "find", "lookup", "google", "web", "information", "article"
        ]):
            capabilities.add("search")
        
        # Check for general conversation keywords
        # This will match common conversation starters and questions
        if any(keyword in message_lower for keyword in [
            "hi", "hello", "hey", "thanks", "thank you", "how are you", 
            "what's up", "who are you", "help me", "explain", "tell me about",
            "what is", "how do", "can you", "please", "would you", "I'm", "I am",
            "I think", "I feel", "I need"
        ]) or message_lower.endswith("?"):
            capabilities.add("assistant")
        
        # If we couldn't detect any specific intent, include "assistant" by default
        # This ensures the general ChatBot will handle the message if no specialized bot can
        if not capabilities:
            capabilities.add("assistant")
            self.logger.info("No specific capabilities detected, defaulting to assistant")
        else:
            self.logger.info(f"Detected capabilities: {capabilities}")
        
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
        
        # Check if there's both ChatBot and specialized bot responses
        chat_bot_response = None
        specialized_responses = []
        
        for response in bot_responses:
            if response["bot_id"] == "chat_bot":
                chat_bot_response = response
            else:
                specialized_responses.append(response)
        
        # If we have both types, prioritize specialized responses
        # but use chat_bot for introduction or transitions
        if chat_bot_response and specialized_responses:
            combined = ""
            
            # Add specialized bot responses with their names
            for i, response in enumerate(specialized_responses):
                combined += f"**{response['bot_name']}**: {response['response']}"
                if i < len(specialized_responses) - 1:
                    combined += "\n\n"
            
            return combined
        
        # Otherwise, just combine all responses with bot names
        combined = ""
        for i, response in enumerate(bot_responses):
            if len(bot_responses) > 1:
                combined += f"**{response['bot_name']}**: {response['response']}"
            else:
                combined += response["response"]
            
            # Add spacing between responses
            if i < len(bot_responses) - 1:
                combined += "\n\n"
        
        return combined
    
    async def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get context for a conversation"""
        # Get recent messages
        messages = await self.database.get_conversation_history(conversation_id, limit=10)
        
        # Get any stored context for this conversation
        stored_context = await self.database.get_conversation_context(conversation_id)
        
        # Combine into a complete context object
        context = {
            "messages": messages,
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            **stored_context
        }
        
        return context
    
    async def update_conversation_context(self, conversation_id: str, updates: Dict[str, Any]):
        """Update context for a conversation"""
        await self.database.update_conversation_context(conversation_id, updates)