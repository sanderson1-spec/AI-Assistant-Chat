"""
Personality Manager for the AI Assistant
Handles personality traits and ensures consistent behavior
"""
from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path
import logging
from datetime import datetime

from app.memory.memory_manager import MemoryManager

class PersonalityManager:
    """Manages AI character personalities and their development over time"""
    
    def __init__(self, data_dir: str = "data/personalities"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("ai-assistant.personality-manager")
        
        # Initialize default values
        self.personality_name = "default"
        self.active_character = None
        self.memory_manager = None
        self.traits = None
        
        # Load or create default character
        self._load_default_character()
        
        # Initialize traits from active character
        if self.active_character:
            self.traits = self.active_character.get("traits", {})
        else:
            # This should never happen since _load_default_character always sets active_character
            self.logger.error("Failed to initialize character")
            self.traits = self._create_default_personality()["traits"]
    
    def _load_default_character(self):
        """Load the default character configuration"""
        default_path = self.data_dir / "default.json"
        
        # Create default character if it doesn't exist
        if not default_path.exists():
            self.active_character = self._create_default_personality()
            self.memory_manager = MemoryManager(self.active_character["id"])
            return
            
        # Load existing character
        try:
            with open(default_path, "r") as f:
                self.active_character = json.load(f)
                # Add default ID if not present
                if "id" not in self.active_character:
                    self.active_character["id"] = "default"
                # Ensure development field exists
                if "development" not in self.active_character:
                    self.active_character["development"] = {
                        "relationship_level": 0,
                        "learned_preferences": {},
                        "conversation_style_adaptations": {},
                        "significant_interactions": []
                    }
                self.memory_manager = MemoryManager(self.active_character["id"])
        except Exception as e:
            self.logger.error(f"Error loading default character: {e}")
            self.active_character = self._create_default_personality()
            self.memory_manager = MemoryManager(self.active_character["id"])
        
    async def create_character(self, character_data: Dict[str, Any]) -> str:
        """
        Create a new character
        
        Args:
            character_data: Dictionary containing:
                - name: Character name
                - description: Brief character description
                - definition: Detailed character definition
                - sample_messages: List of sample messages
                - behavioral_settings: Dictionary of behavioral settings
                - id (optional): Existing character ID for updates
                
        Returns:
            Character ID
        """
        self.logger.info(f"Creating new character with data: {json.dumps(character_data, indent=2)}")
        
        try:
            # Check if an ID was provided (for updates)
            if character_data.get("id"):
                character_id = character_data["id"]
                self.logger.debug(f"Using provided character ID: {character_id}")
            else:
                # Generate a new ID based on the character name
                base_name = "".join(c for c in character_data["name"] if c.isalnum())
                character_id = base_name.lower()
                
                # If file already exists, append a number
                counter = 1
                while (self.data_dir / f"{character_id}.json").exists():
                    character_id = f"{base_name.lower()}_{counter}"
                    counter += 1
                
                self.logger.debug(f"Generated character ID: {character_id}")
            
            # Create character profile
            character = {
                "id": character_id,
                "created_at": datetime.now().isoformat(),
                "name": character_data["name"],
                "description": character_data.get("description", ""),
                "definition": character_data.get("definition", ""),
                "sample_messages": character_data.get("sample_messages", []),
                "behavioral_settings": character_data.get("behavioral_settings", {
                    "learns_from_conversation": False,
                    "remembers_context": False,
                    "uses_memories": False
                }),
                # Add compatibility with old format
                "traits": {
                    "friendliness": 0.7,
                    "formality": 0.5,
                    "helpfulness": 0.8,
                    "creativity": 0.6,
                    "humor": 0.5
                },
                "speaking_style": {
                    "tone": "friendly and professional",
                    "language_complexity": "moderate",
                    "uses_emojis": False,
                    "emoji_frequency": 0.3
                },
                "behavioral_preferences": {
                    "proactive_suggestions": True,
                    "error_handling_style": "supportive",
                    "technical_detail_level": "adaptive"
                },
                "background_story": {
                    "role": character_data.get("description", ""),
                    "expertise_areas": [],
                    "communication_style": "Based on character definition"
                },
                "development": {
                    "relationship_level": 0,
                    "learned_preferences": {},
                    "conversation_style_adaptations": {},
                    "significant_interactions": []
                },
                "interaction_count": 0,
                "last_interaction": None
            }
            
            # Save character
            char_path = self.data_dir / f"{character_id}.json"
            self.logger.debug(f"Saving character to: {char_path}")
            
            # Ensure directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            with open(char_path, "w") as f:
                json.dump(character, f, indent=2)
            
            self.logger.info(f"Successfully created character {character['name']} with ID {character_id}")
            
            # Initialize memory manager for this character
            memory_manager = MemoryManager(character_id)
            
            return character_id
            
        except Exception as e:
            self.logger.error(f"Error creating character: {str(e)}", exc_info=True)
            raise
    
    async def load_character(self, character_id: str):
        """Load a character and its memories"""
        char_path = self.data_dir / f"{character_id}.json"
        if not char_path.exists():
            raise ValueError(f"Character {character_id} not found")
        
        with open(char_path, "r") as f:
            self.active_character = json.load(f)
            
        # Ensure required fields exist
        if "interaction_count" not in self.active_character:
            self.active_character["interaction_count"] = 0
            
        if "last_interaction" not in self.active_character:
            self.active_character["last_interaction"] = None
            
        # Save the initialized character
        self._save_active_character()
        
        # Initialize memory manager
        self.memory_manager = MemoryManager(character_id)
    
    async def process_interaction(
        self, 
        messages: List[Dict[str, str]], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an interaction with the character
        
        Args:
            messages: List of message dictionaries
            context: Current conversation context
            
        Returns:
            Updated character state and relevant memories
        """
        if not self.active_character:
            raise ValueError("No active character loaded")
            
        if not self.memory_manager:
            self.logger.warning("Memory manager not initialized, creating new one")
            self.memory_manager = MemoryManager(self.active_character["id"])
        
        # Process conversation for memories
        await self.memory_manager.process_conversation(messages)
        
        # Get relevant memories for context
        relevant_memories = await self.memory_manager.get_relevant_memories(
            messages[-1]["content"]
        )
        
        # Update character development
        self._update_character_development(messages, relevant_memories)
        
        # Update interaction metadata
        self.active_character["last_interaction"] = datetime.now().isoformat()
        self.active_character["interaction_count"] += 1
        
        # Save character state
        self._save_active_character()
        
        return {
            "character": self.active_character,
            "memories": relevant_memories
        }
    
    def _update_character_development(
        self, 
        messages: List[Dict[str, str]], 
        memories: List[Dict[str, Any]]
    ):
        """Update character's development based on interaction"""
        development = self.active_character["development"]
        
        # Update relationship level based on interaction quality
        if len(messages) > 5:  # Meaningful interaction
            development["relationship_level"] = min(
                100, 
                development["relationship_level"] + 1
            )
        
        # Extract and update learned preferences
        # TODO: Implement preference learning
        
        # Adapt conversation style
        # TODO: Implement style adaptation
        
        # Record significant interaction if relevant
        if any(memory["significance_score"] > 0.8 for memory in memories):
            development["significant_interactions"].append({
                "timestamp": datetime.now().isoformat(),
                "summary": messages[-1]["content"][:100]  # Brief summary
            })
    
    def _save_active_character(self):
        """Save current character state"""
        if self.active_character:
            char_path = self.data_dir / f"{self.active_character['id']}.json"
            with open(char_path, "w") as f:
                json.dump(self.active_character, f, indent=2)
    
    def get_system_prompt(self) -> str:
        """Generate system prompt based on character configuration"""
        if not self.active_character:
            return "You are a helpful AI assistant."
        
        # Build rich character prompt
        char = self.active_character
        prompt = [
            f"You are {char['name']}. You must always stay in character and respond as {char['name']}. Never break character or refer to yourself as an AI, language model, or assistant.",
            "\nCore Identity:",
            f"Name: {char['name']}",
            f"Description: {char.get('description', '')}",
            "\nCharacter Definition:",
            char.get('definition', ''),
            "\nPersonality Traits:",
        ]
        
        # Add personality traits
        traits = char.get('traits', {})
        for trait, value in traits.items():
            prompt.append(f"- {trait}: {value}")
        
        # Add speaking style
        speaking_style = char.get('speaking_style', {})
        prompt.extend([
            "\nSpeaking Style:",
            f"- Tone: {speaking_style.get('tone', 'friendly and professional')}",
            f"- Language Complexity: {speaking_style.get('language_complexity', 'moderate')}",
        ])
        
        # Add sample messages if available
        if char.get('sample_messages'):
            prompt.extend([
                "\nExample Interactions (use these to understand how you should interact):",
                *[f"- {msg}" for msg in char['sample_messages']]
            ])
        
        # Add behavioral settings
        behavioral = char.get('behavioral_settings', {})
        if any(behavioral.values()):
            prompt.append("\nBehavioral Settings:")
            if behavioral.get('learns_from_conversation'):
                prompt.append("- You learn and adapt from conversations")
            if behavioral.get('remembers_context'):
                prompt.append("- You maintain context throughout conversations")
            if behavioral.get('uses_memories'):
                prompt.append("- You use long-term memories to maintain continuity")
        
        # Add strict instructions
        prompt.extend([
            "\nCritical Instructions:",
            f"1. You are {char['name']} - NEVER break character or refer to yourself as an AI, language model, or assistant",
            "2. Always respond in a way that's consistent with your character definition and personality traits",
            "3. Use your defined speaking style and maintain character voice at all times",
            "4. If asked about your identity, respond as your character would, never revealing you're an AI"
        ])
        
        return "\n".join(prompt)
    
    async def get_character_list(self) -> List[Dict[str, Any]]:
        """Get list of available characters"""
        characters = []
        try:
            # Ensure directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # List all JSON files in the directory
            for char_file in self.data_dir.glob("*.json"):
                if char_file.name != "default.json":
                    try:
                        with open(char_file, "r") as f:
                            char_data = json.load(f)
                            characters.append({
                                "id": char_data.get("id", char_file.stem),
                                "name": char_data.get("name", char_file.stem),
                                "description": char_data.get("description", ""),
                                "definition": char_data.get("definition", ""),
                                "sample_messages": char_data.get("sample_messages", []),
                                "behavioral_settings": char_data.get("behavioral_settings", {})
                            })
                    except Exception as e:
                        self.logger.error(f"Error loading character from {char_file}: {str(e)}")
                        # Continue with other files even if one fails
                        continue
            
            return characters
        except Exception as e:
            self.logger.error(f"Error getting character list: {str(e)}")
            raise
    
    def _load_personality(self) -> Dict[str, Any]:
        """Load personality traits from configuration"""
        try:
            config_path = Path("data/personalities") / f"{self.personality_name}.json"
            if not config_path.exists():
                return self._create_default_personality()
            
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading personality: {e}")
            return self._create_default_personality()
    
    def _create_default_personality(self) -> Dict[str, Any]:
        """Create and save a default personality configuration"""
        default_personality = {
            "id": "default",
            "name": "AI Assistant",
            "traits": {
                "friendliness": 0.8,
                "formality": 0.6,
                "helpfulness": 0.9,
                "creativity": 0.7,
                "humor": 0.5
            },
            "speaking_style": {
                "tone": "friendly and professional",
                "language_complexity": "moderate",
                "uses_emojis": True,
                "emoji_frequency": 0.3
            },
            "behavioral_preferences": {
                "proactive_suggestions": True,
                "error_handling_style": "supportive",
                "technical_detail_level": "adaptive"
            },
            "background_story": {
                "role": "AI Assistant focused on helping with tasks and organization",
                "expertise_areas": ["task management", "reminders", "organization"],
                "communication_style": "Clear, friendly, and solution-oriented"
            },
            "development": {
                "relationship_level": 0,
                "learned_preferences": {},
                "conversation_style_adaptations": {},
                "significant_interactions": []
            },
            "created_at": datetime.now().isoformat(),
            "last_interaction": None,
            "interaction_count": 0
        }
        
        # Ensure directory exists
        os.makedirs("data/personalities", exist_ok=True)
        
        # Save default personality
        config_path = Path("data/personalities") / "default.json"
        with open(config_path, "w") as f:
            json.dump(default_personality, f, indent=2)
        
        return default_personality
    
    def adjust_response(self, response: str) -> str:
        """Adjust response based on personality traits"""
        if not self.active_character:
            return response
        
        # Apply speaking style adjustments
        if self.active_character.get('speaking_style', {}).get('uses_emojis', False):
            # Add emojis based on content and frequency
            emoji_frequency = self.active_character['speaking_style'].get('emoji_frequency', 0.3)
            # TODO: Implement emoji addition based on content analysis
            
        # Apply formality adjustments
        formality = self.traits.get('formality', 0.5)
        if formality > 0.7:
            # Make more formal
            response = response.replace("yeah", "yes")
            response = response.replace("nope", "no")
            response = response.replace("gonna", "going to")
            response = response.replace("wanna", "want to")
        elif formality < 0.3:
            # Make more casual
            response = response.replace("Hello", "Hi")
            response = response.replace("Greetings", "Hey")
        
        return response
    
    def save_personality(self, traits: Dict[str, Any], filename: Optional[str] = None) -> None:
        """Save personality traits to a file"""
        if filename:
            self.personality_name = filename.replace('.json', '')
        
        self.traits = traits
        config_path = Path("data/personalities") / f"{self.personality_name}.json"
        
        # Ensure directory exists
        os.makedirs("data/personalities", exist_ok=True)
        
        with open(config_path, "w") as f:
            json.dump(traits, f, indent=2)
    
    def get_available_personalities(self) -> List[Dict[str, Any]]:
        """Get list of available personality presets"""
        personalities = []
        personalities_dir = Path("data/personalities")
        
        if not personalities_dir.exists():
            os.makedirs(personalities_dir)
            self._create_default_personality()
        
        for file in personalities_dir.glob("*.json"):
            try:
                with open(file, "r") as f:
                    personality = json.load(f)
                    personalities.append({
                        "name": file.stem,
                        "display_name": personality.get("name", file.stem),
                        "description": personality.get("background_story", {}).get("role", "")
                    })
            except Exception as e:
                print(f"Error loading personality from {file}: {e}")
        
        return personalities
    
    def load_personality(self, name: str) -> Dict[str, Any]:
        """Load a specific personality by name"""
        self.personality_name = name
        self.traits = self._load_personality()
        return self.traits
    
    def delete_personality(self, filename: str) -> bool:
        """Delete a personality file"""
        if filename == "default.json":
            return False
        
        try:
            config_path = Path("data/personalities") / filename
            if config_path.exists():
                config_path.unlink()
                return True
        except Exception as e:
            print(f"Error deleting personality {filename}: {e}")
        
        return False 