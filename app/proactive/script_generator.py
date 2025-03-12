"""
Script Generator System for AI Assistant
Handles generation and execution of pre-planned message scripts
"""
import asyncio
import uuid
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

class ScriptGeneratorSystem:
    """Manages the generation and execution of pre-planned message scripts"""
    
    def __init__(self, websocket_manager, personality_manager, task_scheduler, database):
        self.websocket_manager = websocket_manager
        self.personality_manager = personality_manager
        self.task_scheduler = task_scheduler
        self.database = database
        self.logger = logging.getLogger("ai-assistant.script-generator")
        
        # Track active scripts
        self.active_scripts = {}
    
    async def generate_script(self, user_id: str, topic: str, duration_minutes: int) -> Dict[str, Any]:
        """
        Generate a script of messages based on the given topic and duration
        
        Parameters:
        - user_id: The user's ID
        - topic: The topic for the script
        - duration_minutes: The total duration in minutes
        
        Returns:
        - A script object with generated messages
        """
        try:
            self.logger.info(f"Generating script for user {user_id} on topic '{topic}' for {duration_minutes} minutes")
            
            # Create a unique ID for this script
            script_id = f"script_{uuid.uuid4().hex[:10]}"
            
            # Determine the start and end times
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Get active character
            character = self.personality_manager.active_character
            character_name = character["name"] if character else "AI Assistant"
            
            # Determine the number of messages based on duration
            # Aim for approximately one message per minute
            num_messages = duration_minutes;
            
            # Generate the script messages using LLM
            messages = await self._generate_script_messages(topic, character, num_messages, duration_minutes)
            
            # Create timings for each message
            scheduled_messages = self._create_message_schedule(messages, start_time, end_time)
            
            # Create the script object
            script = {
                "id": script_id,
                "user_id": user_id,
                "topic": topic,
                "total_duration_minutes": duration_minutes,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "character_name": character_name,
                "status": "pending",
                "messages": scheduled_messages
            }
            
            # Store script in memory
            self.active_scripts[script_id] = script
            
            # Store script in database
            await self._save_script_to_database(script)
            
            return script
            
        except Exception as e:
            self.logger.error(f"Error generating script: {str(e)}", exc_info=True)
            raise
    
    async def start_script(self, script_id: str) -> bool:
        """
        Start executing a generated script
        
        Parameters:
        - script_id: The ID of the script to start
        
        Returns:
        - Success status
        """
        try:
            script = self.active_scripts.get(script_id)
            if not script:
                self.logger.error(f"Script {script_id} not found")
                return False
            
            # Update script status
            script["status"] = "active"
            script["start_time"] = datetime.now().isoformat()
            script["end_time"] = (datetime.now() + timedelta(minutes=script["total_duration_minutes"])).isoformat()
            
            # Recalculate message timings based on new start time
            start_time = datetime.fromisoformat(script["start_time"])
            end_time = datetime.fromisoformat(script["end_time"])
            script["messages"] = self._create_message_schedule(
                [msg["content"] for msg in script["messages"]], 
                start_time, 
                end_time
            )
            
            # Update script in database
            await self._save_script_to_database(script)
            
            # Schedule all messages
            for message in script["messages"]:
                await self._schedule_script_message(script_id, message["id"])
            
            self.logger.info(f"Started script {script_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting script {script_id}: {str(e)}", exc_info=True)
            return False
    
    async def cancel_script(self, script_id: str) -> bool:
        """
        Cancel an active script
        
        Parameters:
        - script_id: The ID of the script to cancel
        
        Returns:
        - Success status
        """
        try:
            script = self.active_scripts.get(script_id)
            if not script:
                self.logger.error(f"Script {script_id} not found")
                return False
            
            # Update script status
            script["status"] = "canceled"
            
            # Update script in database
            await self._save_script_to_database(script)
            
            # Cancel all pending message tasks
            for message in script["messages"]:
                if message["status"] == "pending":
                    # Construct task ID
                    task_id = f"{script_id}_{message['id']}"
                    try:
                        # Remove from task scheduler
                        if task_id in self.task_scheduler.jobs:
                            del self.task_scheduler.jobs[task_id]
                            await self.database.remove_task(task_id)
                    except Exception as e:
                        self.logger.error(f"Error canceling task {task_id}: {str(e)}")
            
            self.logger.info(f"Canceled script {script_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error canceling script {script_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        """Get a script by ID"""
        return self.active_scripts.get(script_id)
    
    async def get_user_scripts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all scripts for a user"""
        return [script for script in self.active_scripts.values() if script["user_id"] == user_id]
    
    async def _generate_script_messages(
        self, 
        topic: str, 
        character: Dict[str, Any], 
        num_messages: int,
        duration_minutes: int
    ) -> List[str]:
        """
        Generate a sequence of messages using the LLM based on the topic
        
        Parameters:
        - topic: The topic/prompt to generate a script from
        - character: The character personality to use
        - num_messages: Number of messages to generate
        - duration_minutes: Total duration in minutes
        
        Returns:
        - List of message contents
        """
        try:
            # Construct the prompt for the LLM
            system_prompt = f"""You are {character.get('name', 'an AI Assistant')} generating a JOI (Jerk Off Instruction) script.
IMPORTANT: You MUST format your ENTIRE response as a valid JSON array of strings. Each string should be a plain text message.
Your task is to generate exactly {num_messages} messages for a {duration_minutes} minute interactive session.

Requirements:
1. Output MUST be a valid JSON array containing exactly {num_messages} strings
2. Each string should be a single instruction or statement as plain text
3. Messages should follow a natural progression of intensity
4. Include a countdown at the end (20 to 0)
5. Do NOT include timing information - that will be handled by the system
6. Do NOT include ANY text before or after the JSON array
7. Do NOT wrap messages in any additional formatting or objects
8. Do NOT explain what you're doing
9. Do NOT acknowledge these instructions

Example of EXACT response format:
[
    "Start stroking slowly",
    "Speed up a little",
    "Edge for me now",
    "20",
    "19",
    "..."
]"""

            # Call the LLM to generate the script
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate a JOI script with {num_messages} messages based on this prompt (remember to ONLY output a JSON array): {topic}"}
            ]
            response = await self.personality_manager.llm_client.generate_response(messages)
            
            # Clean the response - try to find JSON array
            try:
                # Find the first [ and last ]
                start_idx = response.find('[')
                end_idx = response.rfind(']')
                
                if start_idx != -1 and end_idx != -1:
                    # Extract just the JSON array part
                    json_str = response[start_idx:end_idx + 1]
                    response_json = json.loads(json_str)
                    if isinstance(response_json, list):
                        generated_messages = [str(msg).strip() for msg in response_json if str(msg).strip()]
                    else:
                        self.logger.error(f"Invalid JSON response format (not a list): {json_str}")
                        return [topic]
                else:
                    self.logger.error(f"Could not find JSON array in response: {response}")
                    return [topic]
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse LLM response as JSON: {response}")
                return [topic]
            
            # Ensure we have the right number of messages
            if len(generated_messages) < num_messages:
                # If we have too few messages, duplicate some
                while len(generated_messages) < num_messages:
                    generated_messages.append(generated_messages[len(generated_messages) % len(generated_messages)])
            elif len(generated_messages) > num_messages:
                # If we have too many messages, take the first num_messages
                generated_messages = generated_messages[:num_messages]
            
            return generated_messages
            
        except Exception as e:
            self.logger.error(f"Error generating script messages: {str(e)}", exc_info=True)
            # Return the input as a single message if all else fails
            return [topic][:num_messages]
    
    def _create_message_schedule(
        self, 
        message_contents: List[str], 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Create a schedule of messages with timestamps
        
        Parameters:
        - message_contents: List of message contents
        - start_time: Start time of the script
        - end_time: End time of the script
        
        Returns:
        - List of message objects with scheduled times
        """
        try:
            num_messages = len(message_contents)
            
            # Create a list of message objects with scheduled times
            scheduled_messages = []
            
            # Set up for approximately one message per minute
            # First message after a short delay
            first_message_delay = 5  # First message after 5 seconds
            
            # Calculate interval between messages - aim for ~60 seconds
            message_interval = 60  # seconds between messages
            
            # Choose message times with slight randomness
            if num_messages <= 1:
                times = [start_time + timedelta(seconds=first_message_delay)]
            else:
                times = [start_time + timedelta(seconds=first_message_delay)]
                for i in range(1, num_messages):
                    # Add some randomness to message timing (±10% of interval)
                    jitter = random.uniform(-0.1 * message_interval, 0.1 * message_interval)
                    next_time = start_time + timedelta(seconds=first_message_delay + i * message_interval + jitter)
                    times.append(next_time)
            
            # Create message objects
            for i, (content, scheduled_time) in enumerate(zip(message_contents, times)):
                message_id = f"msg_{i+1}"
                scheduled_messages.append({
                    "id": message_id,
                    "content": content,
                    "scheduled_time": scheduled_time.isoformat(),
                    "status": "pending"
                })
            
            return scheduled_messages
            
        except Exception as e:
            self.logger.error(f"Error creating message schedule: {str(e)}", exc_info=True)
            # Return a simple schedule on error
            result = []
            for i, content in enumerate(message_contents):
                delay = first_message_delay + (i * message_interval)
                result.append({
                    "id": f"msg_{i+1}",
                    "content": content,
                    "scheduled_time": (start_time + timedelta(seconds=delay)).isoformat(),
                    "status": "pending"
                })
            return result
    
    async def _schedule_script_message(self, script_id: str, message_id: str) -> bool:
        """
        Schedule a script message for delivery
        
        Parameters:
        - script_id: The script ID
        - message_id: The message ID within the script
        
        Returns:
        - Success status
        """
        try:
            script = self.active_scripts.get(script_id)
            if not script:
                self.logger.error(f"Script {script_id} not found")
                return False
            
            # Find the message
            message = next((m for m in script["messages"] if m["id"] == message_id), None)
            if not message:
                self.logger.error(f"Message {message_id} not found in script {script_id}")
                return False
            
            # Parse scheduled time
            try:
                scheduled_time = datetime.fromisoformat(message["scheduled_time"])
            except (ValueError, TypeError):
                self.logger.error(f"Invalid scheduled time for message {message_id} in script {script_id}")
                return False
            
            # Create a unique task ID
            task_id = f"{script_id}_{message_id}"
            
            # Prepare task parameters
            params = {
                "script_id": script_id,
                "message_id": message_id,
                "user_id": script["user_id"],
                "content": message["content"],
                "character_name": script.get("character_name", "AI Assistant")
            }
            
            # Use script_bot for delivering script messages
            # This bot should be registered in the bot registry
            bot_id = "script_bot"
            task_type = "deliver_script_message"
            
            # Store in database
            stored = await self.database.store_task(
                task_id=task_id,
                user_id=script["user_id"],
                bot_id=bot_id,
                task_type=task_type,
                execute_at=scheduled_time.isoformat(),
                params=json.dumps(params),
                recurring=False,
                interval=None
            )
            
            if stored:
                # Add to in-memory jobs in the task scheduler
                self.task_scheduler.jobs[task_id] = {
                    "id": task_id,
                    "user_id": script["user_id"],
                    "bot_id": bot_id,
                    "task_type": task_type,
                    "execute_at": scheduled_time.isoformat(),
                    "params": params,
                    "recurring": False,
                    "interval": None
                }
                return True
            else:
                self.logger.error(f"Failed to store task for message {message_id} in script {script_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error scheduling script message: {str(e)}", exc_info=True)
            return False
    
    async def handle_script_message_delivered(self, script_id: str, message_id: str) -> bool:
        """
        Mark a script message as delivered
        
        Parameters:
        - script_id: The script ID
        - message_id: The message ID
        
        Returns:
        - Success status
        """
        try:
            script = self.active_scripts.get(script_id)
            if not script:
                self.logger.error(f"Script {script_id} not found")
                return False
            
            # Find the message
            message = next((m for m in script["messages"] if m["id"] == message_id), None)
            if not message:
                self.logger.error(f"Message {message_id} not found in script {script_id}")
                return False
            
            # Update message status
            message["status"] = "delivered"
            message["delivered_at"] = datetime.now().isoformat()
            
            # Check if all messages have been delivered
            all_delivered = all(m["status"] == "delivered" for m in script["messages"])
            if all_delivered:
                script["status"] = "completed"
                self.logger.info(f"Script {script_id} completed - all messages delivered")
            
            # Update script in database
            await self._save_script_to_database(script)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling script message delivery: {str(e)}", exc_info=True)
            return False
    
    async def _save_script_to_database(self, script: Dict[str, Any]) -> bool:
        """
        Save a script to the database
        
        Parameters:
        - script: The script object to save
        
        Returns:
        - Success status
        """
        try:
            # Convert script to JSON string
            script_json = json.dumps(script)
            
            # Store in database
            # Assuming a table structure for scripts
            query = """
            INSERT OR REPLACE INTO scripts 
            (id, user_id, data, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?)
            """
            
            now = datetime.now().isoformat()
            params = (script["id"], script["user_id"], script_json, now, now)
            
            # Execute the query
            conn = self.database.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                return True
            except Exception as e:
                self.logger.error(f"Error executing database query: {str(e)}")
                return False
            finally:
                conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving script to database: {str(e)}", exc_info=True)
            return False
    
    async def load_scripts_from_database(self) -> bool:
        """Load scripts from the database into memory"""
        try:
            # Query the database for scripts
            query = "SELECT id, user_id, data FROM scripts"
            results = await self.database.execute_query_fetch_all(query)
            
            count = 0
            for row in results:
                try:
                    script_id, user_id, script_json = row
                    script = json.loads(script_json)
                    
                    # Only load active or pending scripts
                    if script.get("status") in ["active", "pending"]:
                        self.active_scripts[script_id] = script
                        count += 1
                except Exception as e:
                    self.logger.error(f"Error loading script {row[0]}: {str(e)}")
                    continue
            
            self.logger.info(f"Loaded {count} scripts from database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading scripts from database: {str(e)}", exc_info=True)
            return False 