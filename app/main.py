from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
import uuid
from typing import List, Dict, Optional, Any
import asyncio
from pydantic import BaseModel

from app.database.database import Database
from app.llm.lmstudio_client import LMStudioClient

# Message models for request/response
class EditMessageRequest(BaseModel):
    message_id: int
    content: str

class RegenerateRequest(BaseModel):
    message_id: int
    conversation_id: str
    user_id: str = "default_user"

class VersionSelectRequest(BaseModel):
    message_id: int
    parent_id: int
    conversation_id: str
    user_id: str = "default_user"

# Create FastAPI app
app = FastAPI(title="AI Assistant")

# Set up static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
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
async def get_conversation(conversation_id: str, user_id: str = "default_user"):
    messages = await db.get_conversation_history(conversation_id)
    return {"messages": messages}

@app.get("/api/messages/{message_id}/versions")
async def get_message_versions(message_id: int, user_id: str = "default_user"):
    """Get all response versions for a user message"""
    versions = await db.get_response_versions(message_id)
    return {"versions": versions}

@app.post("/api/messages/{message_id}/edit")
async def edit_message(message_id: int, request: EditMessageRequest):
    """Edit an existing message"""
    success = await db.edit_message(message_id, request.content)
    if success:
        return {"status": "success", "message": "Message updated successfully"}
    else:
        raise HTTPException(status_code=404, detail="Message not found")

@app.post("/api/messages/{message_id}/regenerate")
async def regenerate_response(message_id: int, request: RegenerateRequest):
    """Generate a new response version for a message"""
    # Get the conversation history to maintain context
    messages = await db.get_conversation_history(request.conversation_id)
    
    # Find current message and its content
    user_message = None
    for msg in messages:
        if msg["id"] == message_id:
            user_message = msg
            break
    
    if not user_message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Format message for LLM
    llm_messages = [{"role": "user", "content": user_message["content"]}]
    
    try:
        # Generate new response
        response = await llm_client.generate_response(llm_messages)
        
        # Get existing response versions count
        existing_versions = await db.get_response_versions(message_id)
        new_version = len(existing_versions) + 1
        
        # Store as new version
        response_id = await db.store_response_version(
            user_id=request.user_id,
            content=response,
            parent_id=message_id,
            conversation_id=request.conversation_id,
            version=new_version,
            make_active=True
        )
        
        return {
            "status": "success", 
            "message_id": response_id,
            "content": response,
            "version": new_version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.post("/api/messages/select-version")
async def select_version(request: VersionSelectRequest):
    """Set a specific response version as active"""
    success = await db.set_active_response_version(request.message_id, request.parent_id)
    if success:
        return {"status": "success", "message": "Version activated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to set active version")

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
            edit_message_id = data.get("edit_message_id")  # For editing existing messages
            
            print(f"Received message from client {client_id}: {message[:30]}...")
            
            if edit_message_id:
                # This is an edit, update the existing message
                success = await db.edit_message(edit_message_id, message)
                
                # We need to regenerate the response for this edited message
                # First, delete old responses or mark them as inactive
                # Then generate a new response (similar to regenerate endpoint)
                
                # For simplicity in the WebSocket case, we'll just get a new response
                message_id = edit_message_id
            else:
                # Store user message
                message_id, conv_id = await db.store_message(
                    user_id, 
                    message, 
                    "user", 
                    conversation_id
                )
                conversation_id = conv_id
            
            # For simplicity, let's just use the latest message
            # This mimics your curl test which only sent one message
            llm_messages = [{"role": "user", "content": message}]
            
            # Generate response from LLM
            try:
                print("Requesting response from LMStudio...")
                response = await llm_client.generate_response(llm_messages)
                print(f"Received response from LMStudio: {response[:30]}...")
            except Exception as e:
                import traceback
                print(f"Error calling LMStudio: {str(e)}")
                print(traceback.format_exc())
                response = f"Error connecting to LMStudio: {str(e)}"
            
            # Store assistant message with parent_id reference
            assistant_message_id, _ = await db.store_message(
                user_id=user_id, 
                content=response, 
                role="assistant", 
                conversation_id=conversation_id,
                parent_id=message_id,
                version=1
            )
            
            # Send response back to client
            await manager.send_message(client_id, {
                "type": "message",
                "conversation_id": conversation_id,
                "content": response,
                "role": "assistant",
                "id": assistant_message_id,
                "parent_id": message_id,
                "version": 1,
                "edit_message_id": edit_message_id  # Pass back the edit ID if this was an edit
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