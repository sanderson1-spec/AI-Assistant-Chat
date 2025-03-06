from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
import uuid
from typing import List, Dict, Optional
import asyncio

from app.database.database import Database
from app.llm.lmstudio_client import LMStudioClient

# Create FastAPI app
app = FastAPI(title="AI Assistant")

# Set up static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/static/css", StaticFiles(directory="app/static/css"), name="css")
app.mount("/static/js", StaticFiles(directory="app/static/js"), name="js")
templates = Jinja2Templates(directory="app/static")

# Initialize database
db = Database(db_path="data/assistant.db")

# Initialize LMStudio client
lmstudio_url = os.environ.get("LMSTUDIO_URL", "http://192.168.178.182:1234/v1")
llm_client = LMStudioClient(base_url=lmstudio_url)
print(f"Connecting to LMStudio at: {lmstudio_url}")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

manager = ConnectionManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/conversations")
async def get_conversations(user_id: str = "default_user"):
    conversations = await db.get_recent_conversations(user_id)
    return {"conversations": conversations}

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user_id: str = "default_user", include_all_versions: bool = True):
    messages = await db.get_conversation_history(conversation_id, include_all_versions=include_all_versions)
    return {"messages": messages}

@app.get("/api/messages/{message_id}/versions")
async def get_message_versions(message_id: str, role: str = "assistant"):
    versions = await db.get_message_versions(message_id, role)
    return {"versions": versions}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Process the incoming message
            user_id = data.get("user_id", "default_user")
            message = data.get("message", "")
            conversation_id = data.get("conversation_id")
            is_regeneration = data.get("regenerate", False)
            is_edit = data.get("edit", False)
            original_message_id = data.get("original_message_id")
            
            print(f"Received message from client {client_id}: {message[:30]}...")
            
            # Store user message
            message_metadata = {}
            if is_edit and original_message_id:
                message_metadata["edited"] = True
                message_metadata["originalId"] = original_message_id
                message_id = original_message_id
            else:
                message_id = f"msg_{uuid.uuid4()}"
                
            # Store the user message
            db_message_id, conv_id, stored_message_id = await db.store_message(
                user_id, 
                message, 
                "user", 
                conversation_id,
                metadata=message_metadata,
                message_id=message_id
            )
            
            # For simplicity, let's just use the latest message
            # This mimics your curl test which only sent one message
            llm_messages = [{"role": "user", "content": message}]
            
            # Generate response from LLM
            try:
                print("Requesting response from LMStudio...")
                print(f"Sending message: {json.dumps(llm_messages)}")
                response = await llm_client.generate_response(llm_messages)
                print(f"Received response from LMStudio: {response[:30]}...")
            except Exception as e:
                import traceback
                print(f"Error calling LMStudio: {str(e)}")
                print(traceback.format_exc())
                response = f"Error connecting to LMStudio: {str(e)}"
            
            # Store assistant message
            assistant_metadata = {"responseToId": stored_message_id}
            _, _, assistant_message_id = await db.store_message(
                user_id, 
                response, 
                "assistant", 
                conv_id, 
                metadata=assistant_metadata,
                response_to_id=stored_message_id,
                is_regeneration=is_regeneration
            )
            
            # Send response back to client
            await manager.send_message(client_id, {
                "type": "message",
                "conversation_id": conv_id,
                "content": response,
                "role": "assistant",
                "message_id": assistant_message_id,
                "response_to_id": stored_message_id
            })

    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error with client {client_id}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        manager.disconnect(client_id)

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = "default_user"):
    success = await db.delete_conversation(conversation_id)
    if success:
        return {"status": "success", "message": f"Conversation {conversation_id} deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

@app.delete("/api/conversations")
async def clear_all_conversations(user_id: str = "default_user"):
    count = await db.clear_all_conversations(user_id)
    return {"status": "success", "message": f"Deleted {count} conversations"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)