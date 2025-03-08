"""
Unit tests for the ChatBot
"""
import asyncio
import unittest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime

# Import the ChatBot class
from app.bots.chat_bot import ChatBot

class TestChatBot(unittest.TestCase):
    """Test cases for the ChatBot"""
    
    def setUp(self):
        """Set up test environment"""
        self.chat_bot = ChatBot()
        
        # Create a mock database
        self.mock_db = MagicMock()
        self.mock_db.get_bot_data.return_value = None
        self.chat_bot.database = self.mock_db
    
    def test_init(self):
        """Test ChatBot initialization"""
        self.assertEqual(self.chat_bot.id, "chat_bot")
        self.assertEqual(self.chat_bot.name, "Chat Assistant")
        self.assertEqual(len(self.chat_bot.capabilities), 1)
        self.assertEqual(self.chat_bot.capabilities[0].name, "assistant")
    
    def test_identify_intent_greeting(self):
        """Test intent identification for greetings"""
        greetings = ["hi", "hello", "hey there", "good morning", "howdy partner"]
        for greeting in greetings:
            self.assertEqual(self.chat_bot._identify_intent(greeting), "greeting")
    
    def test_identify_intent_farewell(self):
        """Test intent identification for farewells"""
        farewells = ["goodbye", "bye now", "see you later", "farewell my friend", "have a nice day"]
        for farewell in farewells:
            self.assertEqual(self.chat_bot._identify_intent(farewell), "farewell")
    
    def test_identify_intent_question(self):
        """Test intent identification for questions"""
        questions = ["what is the time?", "how are you today?", "where can I find this?", 
                    "can you help me?", "tell me about yourself"]
        for question in questions:
            self.assertEqual(self.chat_bot._identify_intent(question), "question")
    
    def test_identify_intent_gratitude(self):
        """Test intent identification for expressions of gratitude"""
        gratitude = ["thanks a lot", "thank you so much", "appreciate your help", "grateful for your assistance"]
        for thanks in gratitude:
            self.assertEqual(self.chat_bot._identify_intent(thanks), "gratitude")
    
    def test_identify_intent_general(self):
        """Test intent identification for general conversation"""
        general = ["just thinking about stuff", "I like pizza", "the weather is nice today", "interesting topic"]
        for msg in general:
            self.assertEqual(self.chat_bot._identify_intent(msg), "general")
    
    def test_process_message_greeting(self):
        """Test processing greeting messages"""
        message = "hello there"
        context = {"messages": []}
        
        # Run the async method in the event loop
        response = asyncio.run(self.chat_bot.process_message("user123", message, context))
        
        self.assertIn("response", response)
        self.assertIn("context_updates", response)
        self.assertTrue(response["context_updates"]["has_greeted"])
        self.assertIn("Good", response["response"])  # Should have time-appropriate greeting
    
    def test_process_message_question(self):
        """Test processing question messages"""
        message = "what can you do?"
        context = {"messages": [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "Hi there!"}]}
        
        # Run the async method in the event loop
        response = asyncio.run(self.chat_bot.process_message("user123", message, context))
        
        self.assertIn("response", response)
        self.assertIn("I can help", response["response"].lower())
    
    def test_first_interaction(self):
        """Test detection of first interaction"""
        # Empty context should be first interaction
        self.assertTrue(self.chat_bot._is_first_interaction({}))
        self.assertTrue(self.chat_bot._is_first_interaction({"messages": []}))
        
        # Context with messages should not be first interaction
        self.assertFalse(self.chat_bot._is_first_interaction({
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        }))
        
        # Context with has_greeted flag should not be first interaction
        self.assertFalse(self.chat_bot._is_first_interaction({"has_greeted": True}))

if __name__ == '__main__':
    unittest.main()