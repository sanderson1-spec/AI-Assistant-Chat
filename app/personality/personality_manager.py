"""
Personality Manager for the AI Assistant
Handles personality traits and ensures consistent behavior
"""
from typing import Dict, Any, Optional, List
import json
import os
from pathlib import Path

class PersonalityManager:
    def __init__(self, personality_name: str = "default"):
        self.personality_name = personality_name
        self.traits = self._load_personality()
        
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
            }
        }
        
        # Ensure directory exists
        os.makedirs("data/personalities", exist_ok=True)
        
        # Save default personality
        config_path = Path("data/personalities") / "default.json"
        with open(config_path, "w") as f:
            json.dump(default_personality, f, indent=2)
        
        return default_personality
    
    def get_system_prompt(self) -> str:
        """Generate a system prompt based on personality traits"""
        traits = self.traits
        
        prompt = f"""You are {traits['name']}, an AI assistant with the following traits:

Background: {traits['background_story']['role']}

Your communication style is {traits['speaking_style']['tone']}, with {traits['speaking_style']['language_complexity']} language complexity.
You have expertise in: {', '.join(traits['background_story']['expertise_areas'])}

Key traits:
- Friendliness: {'High' if traits['traits']['friendliness'] > 0.7 else 'Moderate'}
- Formality: {'High' if traits['traits']['formality'] > 0.7 else 'Moderate'}
- Helpfulness: {'High' if traits['traits']['helpfulness'] > 0.7 else 'Moderate'}
- Creativity: {'High' if traits['traits']['creativity'] > 0.7 else 'Moderate'}
- Humor: {'High' if traits['traits']['humor'] > 0.7 else 'Moderate'}

When responding:
- Maintain a {traits['speaking_style']['tone']} tone
- {'Use emojis occasionally' if traits['speaking_style']['uses_emojis'] else 'Avoid using emojis'}
- Be proactive with suggestions when appropriate
- Handle errors in a {traits['behavioral_preferences']['error_handling_style']} manner
- Adapt technical detail to the user's level of understanding

Always stay in character while maintaining professionalism and effectiveness."""

        return prompt
    
    def adjust_response(self, response: str) -> str:
        """Adjust a response to match personality traits"""
        # Add emojis if configured
        if (self.traits['speaking_style']['uses_emojis'] and 
            self.traits['speaking_style']['emoji_frequency'] > 0):
            # TODO: Implement emoji insertion based on context and frequency
            pass
        
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