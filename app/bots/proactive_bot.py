"""
ProactiveBot - A specialized bot for sending proactive messages and task follow-ups
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random

from app.bots.bot_framework import BaseBot, BotCapability

logger = logging.getLogger("ai-assistant.proactive-bot")

class ProactiveBot(BaseBot):
    """Bot for sending proactive messages and task follow-ups"""
    
    def __init__(self, llm_client=None):
        super().__init__(
            bot_id="proactive_bot",
            name="Proactive Assistant",
            description="I proactively engage in conversations and follow up on tasks."
        )
        
        self.llm_client = llm_client
        
        # Register capabilities
        self.register_capability(BotCapability(
            name="proactive",
            description="Send proactive messages and follow up on tasks",
            keywords=["follow up", "check in", "remind", "status"],
            priority=5
        ))
        
        # Register task types
        self.register_task_type("proactive_message")
        self.register_task_type("task_followup")
        
        logger.info("ProactiveBot initialized")
    
    async def process_message(self, user_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process messages and schedule follow-ups if needed"""
        # We don't need to process incoming messages directly
        return {"response": None}
    
    async def execute_task(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scheduled tasks for proactive messaging and follow-ups"""
        if task_type == "proactive_message":
            return await self._handle_proactive_message(params)
        elif task_type == "task_followup":
            return await self._handle_task_followup(params)
        
        logger.warning(f"Unknown task type: {task_type}")
        return {"success": False, "error": "Unknown task type"}
    
    async def _handle_proactive_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate and send a proactive message based on conversation history"""
        user_id = params.get("user_id")
        conversation_id = params.get("conversation_id")
        
        if not self.llm_client:
            return {"success": False, "error": "LLM client not available"}
        
        try:
            # Get recent conversation history
            messages = []
            if conversation_id:
                context = await self.get_conversation_context(conversation_id)
                if context and "messages" in context:
                    messages = context["messages"]
            
            # Prepare prompt for proactive message
            system_prompt = """You are a proactive AI assistant. Based on the conversation history provided, 
            generate a natural, contextually relevant follow-up message. This should feel like a natural continuation 
            of the conversation. Focus on:
            1. Previous topics that might need follow-up
            2. Decisions or plans that were discussed
            3. General check-ins about mentioned activities
            
            Return ONLY the message, no explanations."""
            
            # Convert conversation history to format LLM expects
            llm_messages = [{"role": "system", "content": system_prompt}]
            if messages:
                history = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-5:]])  # Last 5 messages
                llm_messages.append({"role": "user", "content": f"Conversation history:\n{history}"})
            
            # Generate proactive message
            proactive_message = await self.llm_client.generate_response(llm_messages)
            
            # Schedule next proactive message (random interval between 30-60 minutes)
            next_interval = random.randint(30, 60)
            next_time = datetime.now() + timedelta(minutes=next_interval)
            
            return {
                "success": True,
                "notifications": [{
                    "message": proactive_message,
                    "metadata": {"type": "proactive"}
                }],
                "scheduled_tasks": [{
                    "type": "proactive_message",
                    "execute_at": next_time,
                    "params": {
                        "user_id": user_id,
                        "conversation_id": conversation_id
                    }
                }]
            }
        except Exception as e:
            logger.error(f"Error generating proactive message: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _handle_task_followup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle follow-ups for tasks"""
        task_text = params.get("task_text")
        deadline = params.get("deadline")
        status = params.get("status", "pending")  # pending, reminder, overdue
        
        if not task_text or not deadline:
            return {"success": False, "error": "Missing task information"}
        
        try:
            deadline_dt = datetime.fromisoformat(deadline)
            now = datetime.now()
            
            # Generate appropriate follow-up message based on status
            if status == "pending":
                # This is a reminder before the deadline
                time_left = deadline_dt - now
                minutes_left = time_left.total_seconds() / 60
                
                if minutes_left <= 5:
                    message = f"⚠️ Your task '{task_text}' is due in just {int(minutes_left)} minutes!"
                    next_status = "overdue"
                    next_time = deadline_dt
                else:
                    message = f"Reminder: Your task '{task_text}' is due in {int(minutes_left)} minutes."
                    next_status = "pending"
                    next_time = now + timedelta(minutes=minutes_left/2)  # Reminder halfway to deadline
            
            elif status == "overdue":
                message = f"❗ The deadline for '{task_text}' has passed. Please update me on the status."
                next_status = None  # No more follow-ups
                next_time = None
            
            notifications = [{"message": message, "metadata": {"type": "task_followup"}}]
            
            # Schedule next follow-up if needed
            scheduled_tasks = []
            if next_status and next_time:
                scheduled_tasks.append({
                    "type": "task_followup",
                    "execute_at": next_time,
                    "params": {
                        "task_text": task_text,
                        "deadline": deadline,
                        "status": next_status
                    }
                })
            
            return {
                "success": True,
                "notifications": notifications,
                "scheduled_tasks": scheduled_tasks
            }
            
        except Exception as e:
            logger.error(f"Error handling task followup: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)} 