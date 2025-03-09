from datetime import datetime
import json
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path
import nltk
from nltk.tokenize import sent_tokenize

# Check if transformers is available
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not available. Memory analysis will be limited.")

class MemoryManager:
    """Manages long-term memory storage and retrieval for characters"""
    
    def __init__(self, character_id: str, data_dir: str = "data/memories"):
        self.character_id = character_id
        self.data_dir = Path(data_dir) / character_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("ai-assistant.memory-manager")
        
        # Initialize sentiment and zero-shot classifiers if available
        self.sentiment_analyzer = None
        self.zero_shot_classifier = None
        if TRANSFORMERS_AVAILABLE:
            try:
                self.sentiment_analyzer = pipeline("sentiment-analysis")
                self.zero_shot_classifier = pipeline("zero-shot-classification")
            except Exception as e:
                self.logger.warning(f"Error initializing transformers: {e}")
        
        # Load existing memories
        self.memories = self._load_memories()
        
        # Define life event categories
        self.life_event_categories = [
            "career", "relationship", "health", "education",
            "living_situation", "personal_achievement", "goal",
            "preference_change", "emotional_state"
        ]
    
    def _load_memories(self) -> Dict[str, Any]:
        """Load all memories from storage"""
        memory_file = self.data_dir / "memories.json"
        if memory_file.exists():
            with open(memory_file, "r") as f:
                return json.load(f)
        return {
            "critical_events": [],
            "important_context": [],
            "general_knowledge": [],
            "memory_index": {}  # For quick lookups and connections
        }
    
    def _save_memories(self):
        """Save memories to persistent storage"""
        memory_file = self.data_dir / "memories.json"
        with open(memory_file, "w") as f:
            json.dump(self.memories, f, indent=2)
    
    async def process_conversation(self, messages: List[Dict[str, str]]):
        """
        Process a conversation to extract and store important information
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
        """
        for message in messages:
            if message["role"] == "user":
                # Analyze message for significance
                significance = await self._analyze_significance(message["content"])
                
                if significance["is_significant"]:
                    # Create memory entry
                    memory = {
                        "content": message["content"],
                        "timestamp": datetime.now().isoformat(),
                        "significance_score": significance["score"],
                        "categories": significance["categories"],
                        "sentiment": significance["sentiment"],
                        "connections": [],  # Will be filled by memory consolidation
                        "last_recalled": None
                    }
                    
                    # Store in appropriate category
                    if significance["score"] > 0.8:
                        self.memories["critical_events"].append(memory)
                    elif significance["score"] > 0.5:
                        self.memories["important_context"].append(memory)
                    else:
                        self.memories["general_knowledge"].append(memory)
                    
                    # Update memory index
                    self._update_memory_index(memory)
                    
                    # Save changes
                    self._save_memories()
    
    async def _analyze_significance(self, text: str) -> Dict[str, Any]:
        """
        Analyze text for significance using NLP
        
        Returns:
            Dictionary containing significance analysis
        """
        # Default values if transformers not available
        sentiment = {"label": "NEUTRAL", "score": 0.5}
        categories = []
        
        # Perform sentiment analysis if available
        if self.sentiment_analyzer:
            try:
                sentiment = self.sentiment_analyzer(text)[0]
            except Exception as e:
                self.logger.warning(f"Error in sentiment analysis: {e}")
        
        # Perform zero-shot classification if available
        category_result = {"scores": [0.0], "labels": []}
        if self.zero_shot_classifier:
            try:
                category_result = self.zero_shot_classifier(
                    text,
                    candidate_labels=self.life_event_categories
                )
            except Exception as e:
                self.logger.warning(f"Error in zero-shot classification: {e}")
        
        # Calculate significance score based on multiple factors
        significance_score = self._calculate_significance(
            text, sentiment, category_result
        )
        
        return {
            "is_significant": significance_score > 0.3,
            "score": significance_score,
            "categories": [
                label for score, label in 
                zip(category_result["scores"], category_result["labels"])
                if score > 0.3
            ],
            "sentiment": sentiment
        }
    
    def _calculate_significance(
        self, text: str, sentiment: Dict[str, Any], 
        category_result: Dict[str, Any]
    ) -> float:
        """Calculate overall significance score"""
        # Base factors for significance
        factors = [
            len(text) / 500,  # Length factor (normalized)
            abs(sentiment["score"] - 0.5) * 2,  # Strong sentiment (positive or negative)
            max(category_result["scores"]) if category_result["scores"] else 0.0,  # Strongest category match
        ]
        
        # Additional factors
        if any(word in text.lower() for word in [
            "always", "never", "forever", "change", "decided",
            "important", "significant", "remember"
        ]):
            factors.append(0.8)
        
        # Average all factors
        return sum(factors) / len(factors)
    
    def _update_memory_index(self, memory: Dict[str, Any]):
        """Update the memory index with new connections"""
        # Extract key terms
        terms = set(word.lower() for word in nltk.word_tokenize(memory["content"]))
        
        # Update index
        for term in terms:
            if term not in self.memories["memory_index"]:
                self.memories["memory_index"][term] = []
            self.memories["memory_index"][term].append({
                "timestamp": memory["timestamp"],
                "categories": memory["categories"]
            })
    
    async def get_relevant_memories(
        self, current_context: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories relevant to the current conversation context
        
        Args:
            current_context: Current conversation text
            limit: Maximum number of memories to return
            
        Returns:
            List of relevant memories
        """
        # Extract key terms from current context using standard punkt tokenizer
        try:
            current_terms = set(word.lower() for word in nltk.word_tokenize(current_context))
        except Exception as e:
            self.logger.error(f"Error tokenizing text: {str(e)}")
            # Fallback to simple word splitting
            current_terms = set(word.lower() for word in current_context.split())
        
        # Find memories with matching terms
        relevant_memories = []
        for term in current_terms:
            if term in self.memories["memory_index"]:
                for memory_ref in self.memories["memory_index"][term]:
                    # Find full memory from reference
                    memory = self._find_memory_by_timestamp(memory_ref["timestamp"])
                    if memory:
                        relevant_memories.append(memory)
        
        # Sort by significance and recency
        relevant_memories.sort(
            key=lambda x: (x["significance_score"], x["timestamp"]),
            reverse=True
        )
        
        return relevant_memories[:limit]
    
    def _find_memory_by_timestamp(self, timestamp: str) -> Optional[Dict[str, Any]]:
        """Find a memory across all categories by timestamp"""
        for category in ["critical_events", "important_context", "general_knowledge"]:
            for memory in self.memories[category]:
                if memory["timestamp"] == timestamp:
                    return memory
        return None
    
    async def consolidate_memories(self):
        """
        Periodically run to organize and connect memories
        - Identify patterns
        - Update significance scores
        - Archive old, less relevant memories
        """
        # TODO: Implement sophisticated memory consolidation
        # This is a placeholder for future implementation
        pass 