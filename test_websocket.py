import asyncio
import websockets
import json

async def test_websocket():
    uri = 'ws://localhost:8082/ws/test-client'
    async with websockets.connect(uri) as websocket:
        # Send initial connect message
        await websocket.send(json.dumps({
            'type': 'connect',
            'user_id': 'default_user',
            'client_id': 'test-client'
        }))
        
        # Send test message
        await websocket.send(json.dumps({
            'type': 'message',
            'user_id': 'default_user',
            'message': 'Hi Jess, I need to check in with you at 10 PM tonight about my progress on the writing assignment. Can you remind me?',
            'conversation_id': None
        }))
        
        # Wait for response
        response = await websocket.recv()
        print(f'Received: {response}')

asyncio.run(test_websocket()) 