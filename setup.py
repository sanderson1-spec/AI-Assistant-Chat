"""
Setup script for AI Assistant
Creates necessary directories and initializes required components
"""
import os
from pathlib import Path
import json
import nltk

def setup():
    """Set up the AI Assistant environment"""
    print("Setting up AI Assistant...")
    
    # Create required directories
    directories = [
        "data",
        "data/personalities",
        "data/memories",
        "data/vector_db",
        "data/conversations",
        "app/static/js",
        "app/static/css",
        "app/templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Create default personality if it doesn't exist
    default_personality_path = Path("data/personalities/default.json")
    if not default_personality_path.exists():
        default_personality = {
            "name": "AI Assistant",
            "traits": {
                "friendliness": 0.8,
                "formality": 0.6,
                "helpfulness": 0.9,
                "creativity": 0.7,
                "humor": 0.5
            },
            "communication_style": {
                "emoji_use": "moderate",
                "message_length": "medium",
                "technical_level": "adaptive"
            },
            "expertise_areas": [
                "general knowledge",
                "task management",
                "coding assistance",
                "technical support"
            ]
        }
        
        with open(default_personality_path, "w") as f:
            json.dump(default_personality, f, indent=2)
        print("Created default personality configuration")
    
    # Download required NLTK data
    print("Downloading required NLTK data...")
    try:
        nltk.download('punkt')
        print("Successfully downloaded NLTK data")
    except Exception as e:
        print(f"Error downloading NLTK data: {e}")
    
    print("Setup completed successfully!")

if __name__ == "__main__":
    setup() 