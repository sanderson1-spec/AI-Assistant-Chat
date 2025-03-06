import aiohttp
import json
import traceback

class LMStudioClient:
    """Client for interacting with locally hosted LMStudio"""
    
    def __init__(self, base_url="http://192.168.178.182:1234/v1", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        print(f"LMStudio client initialized with URL: {base_url}")
    
    async def generate_response(self, messages, max_tokens=500, temperature=0.7):
        """Generate a response from the local LLM"""
        headers = {"Content-Type": "application/json"}
        
        # Format the request payload exactly as in your curl command
        payload = {
            "model": "your-model-id-here",  # This placeholder is fine
            "messages": messages,
            "temperature": temperature
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
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        print(f"Error from LMStudio: {error_text}")
                        return f"Error: Failed to get response from LLM (Status {response.status}). Error: {error_text}"
        except Exception as e:
            print(f"Exception when calling LMStudio: {str(e)}")
            print(traceback.format_exc())
            return "Error: Could not connect to LMStudio. Exception: " + str(e)