"""
Test script to verify bot registration and capability mapping
"""
import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import components
from app.database.database import Database
from app.bots.bot_framework import BotRegistry, BaseBot, BotCapability
from app.bots.reminder_bot import ReminderBot

async def test_bot_registration():
    """Test that bots are registered properly with capabilities"""
    # Initialize database
    db = Database(db_path="test_bot_registry.db")
    
    # Initialize bot registry
    registry = BotRegistry(db)
    
    # Create and register a reminder bot
    reminder_bot = ReminderBot()
    registry.register_bot(reminder_bot)
    
    # Print registry state
    print("\n=== Bot Registry State ===")
    state = registry.dump_registry_state()
    print(f"Registered bots: {list(state['bots'].keys())}")
    print(f"Registered capabilities: {list(state['capabilities'].keys())}")
    print(f"Registered tasks: {list(state['tasks'].keys())}")
    
    # Test capability lookup
    print("\n=== Capability Tests ===")
    for capability_name in state['capabilities'].keys():
        bots = registry.get_bots_for_capability(capability_name)
        print(f"Bots for capability '{capability_name}': {[bot.id for bot in bots]}")
    
    # Test message parsing
    print("\n=== Message Intent Tests ===")
    test_messages = [
        "Remind me to check email in 5 minutes",
        "Set a reminder for my meeting tomorrow",
        "What are my reminders?",
        "Cancel my reminder about the report"
    ]
    
    for message in test_messages:
        print(f"\nTesting message: '{message}'")
        reminder_info = reminder_bot.extract_reminder_info(message)
        print(f"Extracted intent: {reminder_info}")

async def main():
    await test_bot_registration()

if __name__ == "__main__":
    asyncio.run(main())
