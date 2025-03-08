"""
Main FastAPI application for the AI Assistant with AI Agents integration
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
import uuid
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from app.bots.chat_bot import ChatBot

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("AI_ASSISTANT_DEBUG", "false").lower() in ("true", "1", "yes", "y") else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import existing components
from app.database.database import Database
from app.llm.lmstudio_client import LMStudioClient
from app.config import CONFIG, DEBUG, logger
from app.personality.personality_manager import PersonalityManager

# Import AI Agents components
from app.bots.bot_framework import BotRegistry, BaseBot, BotCapability
from app.bots.reminder_bot import ReminderBot
from app.tasks.task_scheduler import TaskScheduler
from app.notifications.notification_service import NotificationService
from app.controller.central_controller import CentralController
from app.websocket.enhanced_connection_manager import EnhancedConnectionManager

# Message models for request/response (from your existing code)
from pydantic import BaseModel

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

class DeleteMessageRequest(BaseModel):
    message_id: int
    user_id: str = "default_user"

class RewindRequest(BaseModel):
    message_id: int
    user_id: str = "default_user"

# Create a logger for AI Agents
agents_logger = logging.getLogger("ai-assistant.agents")
if DEBUG:
    agents_logger.setLevel(logging.DEBUG)
else:
    agents_logger.setLevel(logging.INFO)

# Create FastAPI app
app = FastAPI(title="AI Assistant")

# Set up static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/static")

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Initialize database
db = Database(db_path=CONFIG["database"]["path"])

# Initialize personality manager
personality_manager = PersonalityManager()

# Initialize LMStudio client with personality
lmstudio_url = CONFIG["lmstudio"]["url"]
llm_client = LMStudioClient(base_url=lmstudio_url, personality_manager=personality_manager)
print(f"Connecting to LMStudio at: {lmstudio_url}")

# Initialize the Enhanced WebSocket connection manager
manager = EnhancedConnectionManager()

# Initialize AI Agents components
bot_registry = BotRegistry(db)
notification_service = NotificationService(db, manager)
task_scheduler = TaskScheduler(db, bot_registry, notification_service)
notification_service.set_task_scheduler(task_scheduler)  # Resolve circular dependency
controller = CentralController(db, bot_registry, task_scheduler, notification_service, llm_client)

# Register specialized bots - will be done in startup event to ensure proper initialization

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Assistant with enhanced architecture")
    
    # Register specialized bots
    logger.info("Registering specialized bots...")
    
    # Initialize and register the reminder bot
    try:
        # First check if dateparser is available
        try:
            import dateparser
            logger.info("Dateparser is available")
        except ImportError:
            logger.warning("Dateparser not installed - ReminderBot will have limited functionality")
        
        # Initialize and register reminder bot
        reminder_bot = ReminderBot()
        bot_registry.register_bot(reminder_bot)
        logger.info(f"Registered ReminderBot with capabilities: {[cap.name for cap in reminder_bot.capabilities]}")
    except Exception as e:
        logger.error(f"Error registering ReminderBot: {str(e)}", exc_info=True)
    
    # Initialize and register chat bot
    try:
        chat_bot = ChatBot()
        bot_registry.register_bot(chat_bot)
        logger.info(f"Registered ChatBot with capabilities: {[cap.name for cap in chat_bot.capabilities]}")
    except Exception as e:
        logger.error(f"Error registering ChatBot: {str(e)}", exc_info=True)

    # List all registered bots and their capabilities
    all_bots = bot_registry.get_all_bots()
    logger.info(f"Registered bots ({len(all_bots)}): {[bot.id for bot in all_bots]}")
    for bot in all_bots:
        logger.info(f"Bot {bot.id} has capabilities: {[cap.name for cap in bot.capabilities]}")
        logger.info(f"Bot {bot.id} has task types: {bot.task_types}")
    
    # List all capabilities in the registry
    all_capabilities = bot_registry.capability_map.keys()
    logger.info(f"Registered capabilities: {list(all_capabilities)}")
    
    # Log whether bots are available for each capability
    for cap in all_capabilities:
        bots = bot_registry.get_bots_for_capability(cap)
        logger.info(f"Capability '{cap}' has {len(bots)} bot(s): {[bot.id for bot in bots]}")
    
    # Dump registry state for debugging
    registry_state = bot_registry.dump_registry_state()
    logger.debug(f"Bot registry state: {json.dumps(registry_state, indent=2)}")
    
    # Initialize the task scheduler
    try:
        await task_scheduler.initialize()
    except Exception as e:
        logger.error(f"Error initializing task scheduler: {str(e)}", exc_info=True)
        # Continue anyway - we can still function without the scheduler for basic chat
    
    logger.info("AI Assistant started successfully")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down AI Assistant")
    
    # Shutdown the task scheduler
    try:
        task_scheduler.shutdown()
    except Exception as e:
        logger.error(f"Error shutting down task scheduler: {str(e)}")

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/api/settings/personality")
async def get_personality_settings():
    """Get current personality settings"""
    return personality_manager.traits

@app.get("/api/settings/personalities")
async def get_available_personalities():
    """Get list of available personality presets"""
    return personality_manager.get_available_personalities()

@app.get("/api/settings/personality/{name}")
async def get_personality(name: str):
    """Get a specific personality by name"""
    try:
        return personality_manager.load_personality(name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Personality not found: {name}")

@app.post("/api/settings/personality")
async def update_personality_settings(settings: Dict[str, Any]):
    """Update personality settings"""
    try:
        personality_manager.save_personality(settings)
        return {"status": "success", "message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/personalities/new")
async def create_new_personality(personality: Dict[str, Any]):
    """Create a new personality preset"""
    try:
        name = personality.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Personality name is required")
        
        # Save as new personality file
        personality_manager.save_personality(personality, f"{name}.json")
        return {"status": "success", "message": f"Created new personality: {name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/settings/personalities/{name}")
async def delete_personality(name: str):
    """Delete a personality preset"""
    try:
        if name == "default":
            raise HTTPException(status_code=400, detail="Cannot delete default personality")
        
        success = personality_manager.delete_personality(f"{name}.json")
        if success:
            return {"status": "success", "message": f"Deleted personality: {name}"}
        else:
            raise HTTPException(status_code=404, detail=f"Personality not found: {name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Existing conversation API routes
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

@app.delete("/api/messages/{message_id}")
async def delete_message(message_id: int, request: DeleteMessageRequest = Body(...)):
    """Delete a specific message and its responses"""
    success = await db.delete_message(message_id)
    if success:
        return {"status": "success", "message": "Message deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Message not found or could not be deleted")

@app.post("/api/messages/{message_id}/rewind")
async def rewind_to_message(message_id: int, request: RewindRequest = Body(...)):
    """Rewind the conversation to a specific message by deleting all later messages"""
    try:
        # Ensure message_id is a valid integer
        if isinstance(message_id, str) and message_id.startswith('temp-'):
            raise HTTPException(
                status_code=400, 
                detail="Cannot rewind to a temporary message ID. Wait for the message to be saved."
            )
        
        # Convert to integer if it's a string that looks like a number
        if isinstance(message_id, str):
            try:
                message_id = int(message_id)
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid message ID format: {message_id}. Expected an integer."
                )
        
        # Now attempt to rewind
        conversation_id = await db.rewind_to_message(message_id)
        if conversation_id:
            # Get the updated conversation
            messages = await db.get_conversation_history(conversation_id)
            return {
                "status": "success", 
                "message": "Conversation rewound successfully",
                "conversation_id": conversation_id,
                "messages": messages
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"Message with ID {message_id} not found or could not rewind conversation"
            )
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"Error in rewind_to_message: {str(e)}")
        print(traceback.format_exc())
        
        # If it's already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise e
            
        # Otherwise, wrap it in a 500 error
        raise HTTPException(
            status_code=500, 
            detail=f"Server error while rewinding conversation: {str(e)}"
        )

# WebSocket endpoint for communication
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    # Accept the connection only once
    await manager.connect(websocket, client_id)
    
    try:
        # First message to get user ID
        data = await websocket.receive_json()
        user_id = data.get("user_id", "default_user")
        
        # Update connection with user ID but don't accept the connection again
        # Just update the tracking in the manager
        manager.add_user_connection(client_id, user_id)
        
        # Send pending notifications for this user
        try:
            notifications = await notification_service.get_user_notifications(user_id)
            if notifications:
                agents_logger.info(f"Sending {len(notifications)} pending notifications to user {user_id}")
                for notification in notifications:
                    await manager.send_message(client_id, {
                        "type": "notification",
                        "id": notification["id"],
                        "message": notification["message"],
                        "source_bot_id": notification.get("source_bot_id"),
                        "metadata": notification.get("metadata"),
                        "timestamp": notification.get("created_at")
                    })
        except Exception as e:
            logger.error(f"Error sending pending notifications: {str(e)}", exc_info=True)
        
        # Process messages
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type", "message")
            
            if message_type == "message":
                # Handle chat message
                user_id = data.get("user_id", "default_user")
                message = data.get("message", "")
                conversation_id = data.get("conversation_id")
                edit_message_id = data.get("edit_message_id")  # For editing existing messages
                
                logger.info(f"Received message from client {client_id}: {message[:30]}...")
                
                if edit_message_id:
                    # This is an edit, update the existing message
                    success = await db.edit_message(edit_message_id, message)
                    
                    # We need to regenerate the response for this edited message
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
                
                # Process with the Central Controller
                try:
                    response = await controller.process_message(user_id, message, conversation_id)
                    
                    # Send response back to client
                    await manager.send_message(client_id, {
                        "type": "message",
                        "conversation_id": response["conversation_id"],
                        "content": response["response"],
                        "role": "assistant",
                        "id": response["message_id"],
                        "parent_id": response["parent_id"],
                        "edit_message_id": edit_message_id  # Pass back the edit ID if this was an edit
                    })
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    # Send error response to client
                    await manager.send_message(client_id, {
                        "type": "message",
                        "conversation_id": conversation_id,
                        "content": "I'm sorry, I encountered an error processing your message. Please try again.",
                        "role": "assistant",
                        "id": 0,  # Temporary ID
                        "parent_id": message_id,
                        "edit_message_id": edit_message_id
                    })
            
            elif message_type == "notification_read":
                # Mark notification as read
                notification_id = data.get("notification_id")
                if notification_id:
                    await notification_service.mark_notification_read(notification_id)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error with client {client_id}: {str(e)}", exc_info=DEBUG)
        import traceback
        logger.error(traceback.format_exc())
        manager.disconnect(client_id)

# Existing conversation management routes
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

# New API routes for AI Agents

# Notification routes
@app.get("/api/notifications")
async def get_notifications(user_id: str = "default_user", include_read: bool = False):
    """Get notifications for a user"""
    notifications = await notification_service.get_user_notifications(user_id, include_read)
    return {"notifications": notifications}

@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int):
    """Mark a notification as read"""
    success = await notification_service.mark_notification_read(notification_id)
    return {"success": success}

# Task routes
@app.get("/api/tasks")
async def get_upcoming_tasks(user_id: str = "default_user"):
    """Get upcoming tasks for a user"""
    tasks = await task_scheduler.get_upcoming_tasks(user_id)
    return {"tasks": tasks}

@app.delete("/api/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a scheduled task"""
    success = await task_scheduler.cancel_task(task_id)
    return {"success": success}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)