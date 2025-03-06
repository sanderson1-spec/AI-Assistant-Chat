"""
FastAPI application main module for the AI Assistant.
Handles HTTP routes and WebSocket connections.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import logging
from typing import Dict

from app.config import CONFIG, DEBUG, logger
from app.database.database import Database
from app.llm.lmstudio_client import LMStudioClient

# Create a module-specific logger
logger = logging.getLogger("ai-assistant.main")

# Create FastAPI app
app = FastAPI(title="AI Assistant")
logger.info("FastAPI application initialized")

# Set up static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/static")
logger.info("Static files and templates configured")

# Initialize database
try:
    db = Database(db_path=CONFIG["database"]["path"])
    logger.info("Database connection established")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}", exc_info=DEBUG)
    raise

# Initialize LMStudio client
try:
    llm_client = LMStudioClient(base_url=CONFIG["lmstudio"]["url"])
    logger.info(f"LMStudio client initialized with URL: {CONFIG['lmstudio']['url']}")
except Exception as e:
    logger.error(f"Failed to initialize LMStudio client: {str(e)}", exc_info=DEBUG)
    raise

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Active connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Remaining connections: {len(self.active_connections)}")
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
            if DEBUG:
                logger.debug(f"Message sent to client {client_id}: {message.get('type')}")

manager = ConnectionManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/conversations")
async def get_conversations(user_id: str = "default_user"):
    try:
        conversations = await db.get_recent_conversations(user_id)
        if DEBUG:
            logger.debug(f"Retrieved {len(conversations)} conversations for user {user_id}")
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error retrieving conversations: {str(e)}", exc_info=DEBUG)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user_id: str = "default_user"):
    try:
        messages = await db.get_conversation_history(conversation_id)
        if DEBUG:
            logger.debug(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error retrieving conversation messages: {str(e)}", exc_info=DEBUG)
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Wait for a message from the client
            data = await websocket.receive_json()
            
            # Process the incoming message
            user_id = data.get("user_id", "default_user")
            message = data.get("message", "")
            conversation_id = data.get("conversation_id")
            
            logger.info(f"Received message from client {client_id}: {message[:30]}...")
            
            # Store user message
            try:
                db_message_id, conv_id, stored_message_id = await db.store_message(
                    user_id, 
                    message, 
                    "user", 
                    conversation_id
                )
                if DEBUG:
                    logger.debug(f"User message stored with ID {db_message_id} in conversation {conv_id}")
            except Exception as e:
                logger.error(f"Error storing user message: {str(e)}", exc_info=DEBUG)
                await manager.send_message(client_id, {
                    "type": "message",
                    "content": f"Error: Could not store your message. Please try again.",
                    "role": "system"
                })
                continue
            
            # Create message for LLM
            llm_messages = [{"role": "user", "content": message}]
            
            # Generate response from LLM
            try:
                logger.info("Requesting response from LMStudio...")
                if DEBUG:
                    logger.debug(f"Sending message to LMStudio: {json.dumps(llm_messages)}")
                
                response = await llm_client.generate_response(llm_messages)
                
                logger.info(f"Received response from LMStudio: {response[:30]}...")
            except Exception as e:
                logger.error(f"Error calling LMStudio: {str(e)}", exc_info=DEBUG)
                response = f"Error connecting to LMStudio. Please check if the server is running and try again."
            
            # Store assistant message
            try:
                await db.store_message(user_id, response, "assistant", conv_id)
                if DEBUG:
                    logger.debug("Assistant response stored in database")
            except Exception as e:
                logger.error(f"Error storing assistant response: {str(e)}", exc_info=DEBUG)
            
            # Send response back to client
            await manager.send_message(client_id, {
                "type": "message",
                "conversation_id": conv_id,
                "content": response,
                "role": "assistant"
            })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error with client {client_id}: {str(e)}", exc_info=DEBUG)
        manager.disconnect(client_id)

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = "default_user"):
    success = await db.delete_conversation(conversation_id)
    if success:
        logger.info(f"Conversation {conversation_id} deleted")
        return {"status": "success", "message": f"Conversation {conversation_id} deleted"}
    else:
        logger.error(f"Failed to delete conversation {conversation_id}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

@app.delete("/api/conversations")
async def clear_all_conversations(user_id: str = "default_user"):
    count = await db.clear_all_conversations(user_id)
    logger.info(f"Deleted {count} conversations for user {user_id}")
    return {"status": "success", "message": f"Deleted {count} conversations"}

# Application startup event
@app.on_event("startup")
async def startup_event():
    logger.info("AI Assistant application started")

# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("AI Assistant application shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)