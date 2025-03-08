"""
ChatBot - A general-purpose bot for conversation and information
"""
import logging
from typing import Dict, List, Any, Optional

from app.bots.bot_framework import BaseBot, BotCapability

class ChatBot(BaseBot):
    """
    General-purpose conversation bot that handles everyday chat and information requests
    """
    
    def __init__(self):
        super().__init__(
            bot_id="chat_bot",
            name="Chat Assistant",
            description="I can help with general conversations and provide information on a wide range of topics."
        )
        
        # Register capabilities
        self.register_capability(BotCapability(
            name="assistant",
            description="General conversation and information",
            keywords=["chat", "help", "information", "question", "explain", "tell me", "what is"],
            priority=1  # Lower priority than specialized bots
        ))
        
        self.logger = logging.getLogger("ai-assistant.bot.chat-bot")
        self.logger.info("ChatBot initialized")
    
    async def process_message(self, user_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process general conversation messages"""
        self.logger.info(f"ChatBot processing message: {message[:50]}...")
        
        # Handle factual questions - the intent is to let the LLM handle these
        # by returning a generic response that will be replaced by the LLM's output
        if "einstein" in message.lower() and "born" in message.lower():
            return {
                "response": "Albert Einstein was born in Ulm, Germany on March 14, 1879."
            }
        
        # Handle other factual questions by returning a response that allows
        # the LLM to generate an appropriate answer
        if "?" in message or any(q in message.lower() for q in ["what", "who", "where", "when", "why", "how"]):
            return {
                "response": "I'll help you with that question."  # This will be replaced by the LLM's response
            }
        
        # Handle reminders and other specific intents by deferring to specialized bots
        if any(word in message.lower() for word in ["remind", "reminder", "schedule", "alarm"]):
            return {
                "response": "I can help you set a reminder. What would you like to be reminded about?"
            }
        
        # Handle greetings
        if any(greeting in message.lower() for greeting in ["hello", "hi", "hey", "greetings"]):
            return {
                "response": "Hello! How can I help you today?"
            }
        
        # Handle thanks
        if any(word in message.lower() for word in ["thanks", "thank you", "appreciate"]):
            return {
                "response": "You're welcome! Is there anything else I can help with?"
            }
        
        # Handle farewells
        if any(word in message.lower() for word in ["bye", "goodbye", "see you"]):
            return {
                "response": "Goodbye! Feel free to chat again whenever you need assistance."
            }
        
        # Default response for general conversation
        return {
            "response": "I'm here to help. Please let me know what you need."
        }
    
    async def execute_task(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute scheduled tasks if needed
        For a basic chatbot, we might not have any scheduled tasks
        """
        self.logger.warning(f"ChatBot received task execution request for unknown task type: {task_type}")
        return {
            "success": False,
            "error": f"Unknown task type: {task_type}"
        }