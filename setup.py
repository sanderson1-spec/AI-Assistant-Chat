"""
Setup script for AI Assistant
Creates necessary directories and initializes required components
"""
import os
from pathlib import Path
import json
import nltk
import logging

def setup_nltk():
    """Download required NLTK data"""
    print("Setting up NLTK data...")
    try:
        # Download required NLTK data
        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        nltk.download('wordnet')
        print("NLTK data downloaded successfully")
    except Exception as e:
        print(f"Error downloading NLTK data: {e}")
        raise

def setup_directories():
    """Create required directories"""
    print("Setting up directories...")
    directories = [
        "data",
        "data/personalities",
        "data/memories",
        "data/vector_db",
        "data/conversations"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

def main():
    """Run all setup tasks"""
    print("Starting AI Assistant setup...")
    
    # Setup directories
    setup_directories()
    
    # Setup NLTK
    setup_nltk()
    
    print("Setup completed successfully!")

if __name__ == "__main__":
    main() 