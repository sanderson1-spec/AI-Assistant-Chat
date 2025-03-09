"""
Proactive messaging system for character-driven interactions
Handles both random check-ins and scheduled follow-ups
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path
import json

class ProactiveSystem:
    """Manages proactive messaging from characters"""
    
    def __init__(self, websocket_manager, personality_manager, task_scheduler):
        self.websocket_manager = websocket_manager
        self.personality_manager = personality_manager
        self.task_scheduler = task_scheduler
        self.logger = logging.getLogger("ai-assistant.proactive")
        
        # Track active conversations and scheduled check-ins
        self.active_conversations = {}
        self.scheduled_checkins = {}
        
        # Configure random check-in parameters
        self.min_interval = timedelta(minutes=30)  # Minimum time between random checks
        self.max_interval = timedelta(hours=4)     # Maximum time between random checks
        
        # Start the random check-in scheduler
        asyncio.create_task(self._schedule_random_checkins())
    
    async def _schedule_random_checkins(self):
        """Schedule random check-ins throughout the day"""
        while True:
            # Calculate next random check-in time
            interval = random.uniform(
                self.min_interval.total_seconds(),
                self.max_interval.total_seconds()
            )
            next_checkin = datetime.now() + timedelta(seconds=interval)
            
            self.logger.debug(f"Scheduled next random check-in for {next_checkin}")
            
            # Wait until next check-in time
            await asyncio.sleep(interval)
            
            # Perform random check-in
            await self._perform_random_checkin()
    
    async def _perform_random_checkin(self):
        """Generate and send a random check-in message"""
        try:
            # Get active character
            character = self.personality_manager.active_character
            if not character:
                return
            
            # Generate a contextual message based on:
            # - Time of day
            # - Previous conversations
            # - Character personality
            current_hour = datetime.now().hour
            
            # Time-based greeting
            if 5 <= current_hour < 12:
                time_context = "morning"
            elif 12 <= current_hour < 17:
                time_context = "afternoon"
            elif 17 <= current_hour < 22:
                time_context = "evening"
            else:
                time_context = "night"
            
            # Get conversation history for context
            # TODO: Implement conversation history retrieval
            
            # Generate message using LLM
            message = await self._generate_checkin_message(time_context, character)
            
            # Send to all active connections
            for client_id in self.websocket_manager.active_connections:
                await self.websocket_manager.send_message(client_id, {
                    "type": "proactive_message",
                    "content": message,
                    "character_name": character["name"],
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            self.logger.error(f"Error in random check-in: {str(e)}", exc_info=True)
    
    async def schedule_followup(
        self,
        scheduled_time: datetime,
        context: Dict[str, Any],
        user_id: str
    ):
        """Schedule a specific follow-up message"""
        # Create a unique ID for this check-in
        checkin_id = f"checkin_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
        
        # Store check-in details
        self.scheduled_checkins[checkin_id] = {
            "time": scheduled_time,
            "context": context,
            "user_id": user_id,
            "status": "pending"
        }
        
        # Schedule the task
        await self.task_scheduler.schedule_task(
            task_type="scheduled_checkin",
            execute_at=scheduled_time,
            params={
                "checkin_id": checkin_id,
                "user_id": user_id,
                "context": context
            }
        )
        
        self.logger.info(f"Scheduled follow-up for {scheduled_time} with ID {checkin_id}")
        return checkin_id
    
    async def _generate_checkin_message(self, time_context: str, character: Dict[str, Any]) -> str:
        """Generate a contextual check-in message"""
        # Prepare prompt for LLM
        prompt = [
            f"You are {character['name']}, checking in with your friend during the {time_context}.",
            "Generate a natural, casual message to start a conversation.",
            "Consider your personality traits:",
        ]
        
        # Add personality context
        for trait, value in character["personality_traits"].items():
            prompt.append(f"- {trait}: {value}")
        
        # Add time context
        prompt.append(f"\nIt's {time_context}.")
        
        # TODO: Add conversation history context
        
        # Use LLM to generate message
        messages = [
            {"role": "system", "content": "\n".join(prompt)},
            {"role": "user", "content": "Generate a natural check-in message"}
        ]
        
        try:
            response = await self.personality_manager.llm_client.generate_response(messages)
            return response.strip()
        except Exception as e:
            self.logger.error(f"Error generating check-in message: {str(e)}", exc_info=True)
            return f"Hey, how are you doing? [Error: {str(e)}]"
    
    async def handle_scheduled_checkin(self, checkin_id: str):
        """Handle a scheduled check-in when its time arrives"""
        try:
            checkin = self.scheduled_checkins.get(checkin_id)
            if not checkin:
                self.logger.error(f"Check-in {checkin_id} not found")
                return
            
            # Generate appropriate follow-up message based on context
            context = checkin["context"]
            message = await self._generate_followup_message(context)
            
            # Send message to specific user
            user_connections = self.websocket_manager.get_user_connections(checkin["user_id"])
            for client_id in user_connections:
                await self.websocket_manager.send_message(client_id, {
                    "type": "scheduled_followup",
                    "content": message,
                    "context": context,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Update check-in status
            checkin["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Error handling scheduled check-in: {str(e)}", exc_info=True)
    
    async def _generate_followup_message(self, context: Dict[str, Any]) -> str:
        """Generate a context-aware follow-up message"""
        try:
            # Get active character
            character = self.personality_manager.active_character
            if not character:
                return "Hey, following up on our previous conversation..."
            
            # Prepare prompt for LLM
            prompt = [
                f"You are {character['name']}, following up on a previous conversation.",
                "Context from previous conversation:",
                json.dumps(context, indent=2),
                "\nGenerate a natural follow-up message considering the context."
            ]
            
            messages = [
                {"role": "system", "content": "\n".join(prompt)},
                {"role": "user", "content": "Generate a natural follow-up message"}
            ]
            
            response = await self.personality_manager.llm_client.generate_response(messages)
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating follow-up message: {str(e)}", exc_info=True)
            return "Hey, I wanted to follow up on our previous conversation..." 