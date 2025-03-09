import aiohttp
import json
import traceback
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re

# Check if dateparser is available
try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    print("Warning: dateparser not available. Task detection will be limited.")

logger = logging.getLogger("ai-assistant.lmstudio")

class LMStudioClient:
    """Client for interacting with locally hosted LMStudio"""
    
    def __init__(self, base_url="http://localhost:1234/v1", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.personality_manager = None
        logger.info(f"LMStudio client initialized with URL: {base_url}")
    
    def set_personality_manager(self, personality_manager):
        """Set the personality manager after initialization"""
        self.personality_manager = personality_manager
        print("Personality manager set for LMStudio client")
    
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
        if self.personality_manager:
            system_prompt = self.personality_manager.get_system_prompt()
            # Remove any existing system message
            messages = [m for m in messages if m["role"] != "system"]
            # Add our system prompt at the start
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Process interaction to get memories if personality manager is available
        if self.personality_manager and len(messages) > 0:
            try:
                interaction_result = await self.personality_manager.process_interaction(
                    messages, context or {}
                )
                
                # If we have relevant memories, add them to the context
                if interaction_result["memories"]:
                    memory_context = "\nRelevant memories and context:\n"
                    for memory in interaction_result["memories"]:
                        memory_context += f"- {memory['content']}\n"
                    
                    # Add memories to system message
                    messages[0]["content"] += "\n" + memory_context
            except Exception as e:
                print(f"Error processing interaction: {str(e)}")
                # Continue without memories if there's an error
        
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
            print(f"Payload: {json.dumps(payload)[:500]}...")  # Log more of the payload for debugging
            
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
                        raise Exception(f"Failed to get response from LLM (Status {response.status}). Error: {error_text}")
        except Exception as e:
            print(f"Exception when calling LMStudio: {str(e)}")
            print(traceback.format_exc())
            raise  # Re-raise the exception to be handled by the caller
    
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

    async def detect_tasks(self, text: str) -> List[Dict[str, str]]:
        """Detect tasks in the given text using LLM with a two-stage approach."""
        logging.debug(f"Analyzing response for tasks: {text[:100]}...")
        
        # STAGE 1: Simple YES/NO classification to detect if tasks exist
        logging.debug("Stage 1: Checking if tasks exist...")
        has_tasks = await self._check_if_tasks_exist(text)
        
        if not has_tasks:
            logging.info("No tasks detected in first stage check")
            return []
        
        # STAGE 2: Detailed task extraction (only if tasks exist)
        logging.debug("Stage 2: Extracting tasks...")
        tasks = await self._extract_tasks_with_llm(text)
        
        # If LLM extraction failed, fall back to rule-based extraction
        if not tasks:
            logging.info("LLM task extraction failed, falling back to rule-based extraction")
            tasks = self._rule_based_task_extraction(text)
            
        return tasks
    
    async def _check_if_tasks_exist(self, text: str) -> bool:
        """First stage: Simple check if tasks exist in the text."""
        prompt = """
        Analyze this text and respond with ONLY 'YES' or 'NO':
        Does this text contain any action items, tasks, planned events, meetings, or deadlines?
        
        Text: {text}
        
        Your answer (ONLY YES or NO):
        """.format(text=text)
        
        try:
            response = await self.generate_response([{"role": "user", "content": prompt}])
            logging.info(f"Task existence check response: {response!r}")
            
            # Look for 'YES' in the response (case insensitive)
            return 'YES' in response.upper()
        except Exception as e:
            logging.error(f"Error in task existence check: {e}")
            # Default to true to err on the side of caution
            return True
    
    async def _extract_tasks_with_llm(self, text: str) -> List[Dict[str, str]]:
        """Second stage: Extract detailed task information using LLM."""
        logging.debug("Generating task analysis...")
        
        prompt = """You are a task detection AI. Your ONLY job is to analyze the following text and extract tasks with deadlines.
IMPORTANT RULES:
1. ONLY output a JSON array. NO other text.
2. Each task MUST have "text" and "deadline" fields.
3. If no tasks found, output empty array: []
4. DO NOT explain what you're doing.
5. DO NOT give examples.
6. DO NOT include any text before or after the JSON array.
7. DO NOT include any conversation or roleplay.
8. ONLY output valid JSON that can be parsed by json.loads().
9. ONLY extract tasks that are ACTUALLY mentioned in the text.
10. DO NOT make up tasks or deadlines.
11. DO NOT use example tasks from these instructions.
12. The deadline MUST be a specific time/date mentioned in the text.
13. If a task has no specific deadline in the text, do not include it.

Here is the text to analyze (output ONLY a JSON array):
{text}"""

        try:
            response = await self.generate_response([{"role": "user", "content": prompt}])
            logging.info(f"Raw task analysis response: {response!r}")

            # Clean up response to ensure it's valid JSON
            # Find the first [ and last ]
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            
            if start_idx == -1:
                logging.warning("No JSON array start found")
                return []
                
            if end_idx == -1:
                logging.warning("No JSON array end found")
                return []
                
            cleaned_response = response[start_idx:end_idx + 1]
            logging.info(f"Cleaned task response: {cleaned_response!r}")
            
            tasks = json.loads(cleaned_response)
            if not isinstance(tasks, list):
                logging.warning(f"Expected list but got {type(tasks)}")
                return []
                
            valid_tasks = []
            for task in tasks:
                if not isinstance(task, dict):
                    logging.warning(f"Expected dict but got {type(task)}")
                    continue
                    
                # Try multiple common field names
                task_text = task.get('text') or task.get('task') or task.get('description')
                task_deadline = task.get('deadline') or task.get('time') or task.get('due')
                
                if not task_text or not task_deadline:
                    logging.warning(f"Skipping task missing required fields: {task}")
                    continue
                    
                try:
                    # Validate deadline can be parsed
                    parsed_deadline = dateparser.parse(task_deadline, settings={'PREFER_DATES_FROM': 'future'})
                    if not parsed_deadline:
                        logging.warning(f"Could not parse deadline: {task_deadline}")
                        continue
                        
                    valid_tasks.append({
                        'text': task_text,
                        'deadline': task_deadline
                    })
                except Exception as e:
                    logging.error(f"Error parsing deadline: {e}")
                    continue
                    
            logging.info(f"Found {len(valid_tasks)} valid tasks")
            return valid_tasks
            
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding task response: {e}")
            logging.error(f"Raw response: {response!r}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in task detection: {e}")
            return []
            
    def _rule_based_task_extraction(self, text: str) -> List[Dict[str, str]]:
        """Fallback method: Extract tasks using rule-based pattern matching."""
        logging.debug("Using rule-based task extraction")
        tasks = []
        
        # Only proceed if dateparser is available
        if not dateparser:
            logging.error("Cannot perform rule-based extraction without dateparser")
            return []
            
        # Split text into sentences
        sentences = re.split(r'[.!?]', text)
        
        # Time indicators to filter relevant sentences
        time_indicators = ['today', 'tomorrow', 'tonight', 'next week', 
                          'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                          'am', 'pm', ':00', 'o\'clock', 'morning', 'afternoon', 'evening']
        
        # Task-related keywords
        task_keywords = ['check-in', 'meeting', 'appointment', 'reminder', 'remember', 'don\'t forget',
                       'need to', 'have to', 'must', 'should', 'assignment', 'deadline', 'due']
        
        for sentence in sentences:
            # Skip empty sentences
            if not sentence.strip():
                continue
                
            # Convert to lowercase for matching
            sentence_lower = sentence.lower()
            
            # Skip sentences without time indicators or task keywords
            if not any(indicator in sentence_lower for indicator in time_indicators) or \
               not any(keyword in sentence_lower for keyword in task_keywords):
                continue
            
            # Extract potential dates using dateparser
            potential_dates = []
            words = sentence.split()
            for i in range(len(words)):
                for j in range(i+1, min(i+8, len(words))):  # Look at phrases up to 7 words long
                    phrase = " ".join(words[i:j])
                    try:
                        parsed_date = dateparser.parse(phrase, settings={'PREFER_DATES_FROM': 'future'})
                        if parsed_date:
                            potential_dates.append({
                                "text": phrase,
                                "date": parsed_date,
                                "start_idx": i,
                                "end_idx": j
                            })
                    except:
                        continue
            
            # If we found a date in this sentence, consider it a task
            if potential_dates:
                # Sort by length of match (longer matches are usually better)
                best_date = sorted(potential_dates, key=lambda x: x["end_idx"] - x["start_idx"], reverse=True)[0]
                
                # Use the original sentence as task text, but remove the date portion
                task_text = sentence.strip()
                deadline_text = best_date["text"]
                
                tasks.append({
                    "text": task_text,
                    "deadline": deadline_text
                })
        
        logging.info(f"Rule-based extraction found {len(tasks)} tasks")
        return tasks