import asyncio
import aiohttp
import json

async def test_lmstudio():
    url = "http://192.168.178.182:1234/v1/chat/completions"
    payload = {
        "model": "darkidol-llama-3.1-8b-instruct-1.2-uncensored",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
    
    print(f"Testing LMStudio API at {url}")
    print(f"Request payload: {json.dumps(payload)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Response status: {response.status}")
                if response.status == 200:
                    result = await response.json()
                    print(f"Success! Response: {json.dumps(result)[:200]}...")
                else:
                    text = await response.text()
                    print(f"Error response: {text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_lmstudio())