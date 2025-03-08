import aiohttp
import json
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class LMStudioClient:
    """Client for interacting with locally hosted LMStudio"""
    
    def __init__(self, base_url="http://192.168.178.182:1234/v1", api_key=None, personality_manager=None):
        self.base_url = base_url
        self.api_key = api_key
        self.personality_manager = personality_manager
        print(f"LMStudio client initialized with URL: {base_url}")
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        context: Optional[Dict[str, Any]] = None, 
        max_tokens: int = 500, 
        temperature: float = 0.7
    ) -> str:
        """Generate a response from the local LLM with personality and context"""
        headers = {"Content-Type": "application/json"}
        
        # Add personality system prompt if available
        if self.personality_manager and not any(m["role"] == "system" for m in messages):
            system_prompt = self.personality_manager.get_system_prompt()
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Add time context to the system message if available
        if context and 'time_context' in context:
            time_context_str = (
                "Current Time Context:\n"
                f"Current Date: {context['time_context']['current_date']}\n"
                f"Current Time: {context['time_context']['current_time']}\n"
                f"Current Day: {context['time_context']['current_day_of_week']}\n"
                f"Tomorrow's Date: {context['time_context']['tomorrow_date']}\n"
                f"Tomorrow's Day: {context['time_context']['tomorrow_day_of_week']}\n"
                f"Timezone: {context['time_context']['timezone']}"
            )
            
            # Append time context to system message if it exists
            if messages[0]["role"] == "system":
                messages[0]["content"] += f"\n\n{time_context_str}"
            else:
                messages.insert(0, {"role": "system", "content": time_context_str})
        
        # Format the request payload
        payload = {
            "model": "your-model-id-here",  # This placeholder is fine
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            endpoint = f"{self.base_url}/chat/completions"
            print(f"Sending request to LMStudio at {endpoint}")
            print(f"Payload: {json.dumps(payload)[:100]}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=headers
                ) as response:
                    print(f"Received response from LMStudio with status: {response.status}")
                    if response.status == 200:
                        result = await response.json()
                        response_text = result["choices"][0]["message"]["content"]
                        
                        # Adjust response based on personality if available
                        if self.personality_manager:
                            response_text = self.personality_manager.adjust_response(response_text)
                        
                        return response_text
                    else:
                        error_text = await response.text()
                        print(f"Error from LMStudio: {error_text}")
                        return f"Error: Failed to get response from LLM (Status {response.status}). Error: {error_text}"
        except Exception as e:
            print(f"Exception when calling LMStudio: {str(e)}")
            print(traceback.format_exc())
            return "Error: Could not connect to LMStudio. Exception: " + str(e)
    
    async def analyze_intent(self, message: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Analyze the intent of a message using the LLM
        
        Args:
            message: The user's message
            context: Additional context for intent analysis
            
        Returns:
            List of detected capabilities
        """
        # Prepare messages for intent analysis
        messages = [
            {
                "role": "system", 
                "content": "You are an intent classifier. Identify the primary capability "
                           "needed to respond to the user's message. Possible capabilities "
                           "are: reminders, todos, calendar, email, search, assistant. "
                           "Return ONLY the capability name. If no specific capability "
                           "is clear, return 'assistant'."
            },
            {"role": "user", "content": message}
        ]
        
        try:
            # Use generate_response to get intent
            intent_response = await self.generate_response(messages, context)
            
            # Clean and validate the intent
            intent = intent_response.strip().lower()
            
            # Validate intent
            valid_intents = ['reminders', 'todos', 'calendar', 'email', 'search', 'assistant']
            
            if intent in valid_intents:
                return [intent]
            
            return ['assistant']
        
        except Exception as e:
            print(f"Error analyzing intent: {str(e)}")
            return ['assistant']