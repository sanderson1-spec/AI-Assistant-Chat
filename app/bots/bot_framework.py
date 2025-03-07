"""
Bot Framework for AI Assistant
Defines the interface and registry for specialized bots
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger("ai-assistant.bot-framework")

class BotCapability:
    """Represents a specific capability a bot can handle"""
    def __init__(self, name: str, description: str, keywords: List[str], priority: int = 1):
        self.name = name
        self.description = description
        self.keywords = keywords
        self.priority = priority
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "priority": self.priority
        }

class BaseBot(ABC):
    """Abstract base class for all specialized bots"""
    
    def __init__(self, bot_id: str, name: str, description: str):
        self.id = bot_id
        self.name = name
        self.description = description
        self.capabilities: List[BotCapability] = []
        self.task_types: List[str] = []
    
    def register_capability(self, capability: BotCapability) -> None:
        """Register a new capability for this bot"""
        self.capabilities.append(capability)
    
    def register_task_type(self, task_type: str) -> None:
        """Register a task type this bot can handle"""
        if task_type not in self.task_types:
            self.task_types.append(task_type)
    
    @abstractmethod
    async def process_message(self, user_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a user message
        
        Args:
            user_id: ID of the user
            message: Text message from the user
            context: Conversation context and history
            
        Returns:
            Dictionary with response and optional scheduled tasks/notifications
            {
                "response": str,                     # Text response to user
                "context_updates": Dict,             # Updates to conversation context
                "scheduled_tasks": List[Dict],       # Tasks to schedule
                "scheduled_notifications": List[Dict] # Notifications to schedule
            }
        """
        pass
    
    @abstractmethod
    async def execute_task(self, task_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a scheduled task
        
        Args:
            task_type: Type of task to execute
            params: Parameters for the task
            
        Returns:
            Result of task execution
            {
                "success": bool,
                "result": Any,
                "notifications": List[Dict]  # Any notifications to be sent
            }
        """
        pass
    
    async def store_bot_data(self, database, user_id: str, key: str, value: Any) -> None:
        """Store bot-specific data for a user"""
        await database.store_bot_data(
            self.id, 
            user_id, 
            key, 
            json.dumps(value) if not isinstance(value, str) else value
        )
    
    async def retrieve_bot_data(self, database, user_id: str, key: str) -> Any:
        """Retrieve bot-specific data for a user"""
        data = await database.get_bot_data(self.id, user_id, key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return data
        return None

class BotRegistry:
    """Registry for managing and accessing specialized bots"""
    
    def __init__(self, database):
        self.bots: Dict[str, BaseBot] = {}
        self.capability_map: Dict[str, List[BaseBot]] = {}
        self.task_map: Dict[str, BaseBot] = {}
        self.database = database
        self.logger = logging.getLogger("ai-assistant.bot-registry")
    
    def register_bot(self, bot: BaseBot) -> None:
        """Register a bot with the system"""
        self.bots[bot.id] = bot
        
        # Register capabilities
        for capability in bot.capabilities:
            if capability.name not in self.capability_map:
                self.capability_map[capability.name] = []
            self.capability_map[capability.name].append(bot)
            
            # Sort by priority (higher first)
            self.capability_map[capability.name].sort(
                key=lambda b: next(
                    (c.priority for c in b.capabilities if c.name == capability.name), 
                    0
                ), 
                reverse=True
            )
        
        # Register task types
        for task_type in bot.task_types:
            self.task_map[task_type] = bot
            
        self.logger.info(f"Registered bot: {bot.id} ({bot.name}) with {len(bot.capabilities)} capabilities")
    
    def unregister_bot(self, bot_id: str) -> None:
        """Unregister a bot from the system"""
        if bot_id not in self.bots:
            return
            
        bot = self.bots[bot_id]
        
        # Remove from capability map
        for capability in bot.capabilities:
            if capability.name in self.capability_map:
                self.capability_map[capability.name] = [
                    b for b in self.capability_map[capability.name] 
                    if b.id != bot_id
                ]
        
        # Remove from task map
        for task_type in bot.task_types:
            if task_type in self.task_map and self.task_map[task_type].id == bot_id:
                del self.task_map[task_type]
        
        # Remove from bots dictionary
        del self.bots[bot_id]
        self.logger.info(f"Unregistered bot: {bot_id}")
    
    def get_bot(self, bot_id: str) -> Optional[BaseBot]:
        """Get a specific bot by ID"""
        return self.bots.get(bot_id)
    
    def get_bots_for_capability(self, capability_name: str) -> List[BaseBot]:
        """Get all bots that provide a specific capability"""
        return self.capability_map.get(capability_name, [])
    
    def get_bot_for_task(self, task_type: str) -> Optional[BaseBot]:
        """Get the bot that handles a specific task type"""
        return self.task_map.get(task_type)
    
    def get_all_bots(self) -> List[BaseBot]:
        """Get all registered bots"""
        return list(self.bots.values())