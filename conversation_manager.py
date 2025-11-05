"""
Conversation management with memory, caching, and threading.
"""
import json
import os
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
import config


class ConversationManager:
    """Manages conversation history, caching, and threading."""
    
    def __init__(self, cache_dir: str = "./cache"):
        """Initialize conversation manager."""
        self.cache_dir = cache_dir
        self.conversations_file = os.path.join(cache_dir, "conversations.json")
        self.cache_file = os.path.join(cache_dir, "question_cache.json")
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load existing data
        self.conversations = self._load_conversations()
        self.question_cache = self._load_cache()
    
    def _load_conversations(self) -> Dict:
        """Load conversation history from file."""
        if os.path.exists(self.conversations_file):
            try:
                with open(self.conversations_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _load_cache(self) -> Dict:
        """Load question cache from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_conversations(self):
        """Save conversation history to file."""
        try:
            with open(self.conversations_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving conversations: {e}")
    
    def _save_cache(self):
        """Save question cache to file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.question_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _hash_question(self, question: str) -> str:
        """Create a hash for a question (normalized)."""
        # Normalize question: lowercase, remove extra spaces
        normalized = " ".join(question.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def find_similar_question(self, question: str, threshold: float = 0.8) -> Optional[Dict]:
        """
        Find similar questions in cache.
        
        Args:
            question: Current question
            threshold: Similarity threshold (0-1)
            
        Returns:
            Cached answer if similar question found, None otherwise
        """
        question_hash = self._hash_question(question)
        
        # Direct match
        if question_hash in self.question_cache:
            cached = self.question_cache[question_hash]
            return {
                "answer": cached.get("answer"),
                "source_documents": cached.get("source_documents", []),
                "similarity": 1.0,
                "original_question": cached.get("question")
            }
        
        # Simple similarity check (basic word overlap)
        normalized_q = set(question.lower().split())
        best_match = None
        best_similarity = 0.0
        
        for cached_hash, cached_data in self.question_cache.items():
            cached_q = cached_data.get("question", "")
            cached_normalized = set(cached_q.lower().split())
            
            if not cached_normalized:
                continue
            
            # Calculate Jaccard similarity
            intersection = len(normalized_q & cached_normalized)
            union = len(normalized_q | cached_normalized)
            similarity = intersection / union if union > 0 else 0.0
            
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = cached_data
        
        if best_match:
            return {
                "answer": best_match.get("answer"),
                "source_documents": best_match.get("source_documents", []),
                "similarity": best_similarity,
                "original_question": best_match.get("question")
            }
        
        return None
    
    def cache_answer(self, question: str, answer: str, source_documents: List[Dict]):
        """Cache a question-answer pair."""
        question_hash = self._hash_question(question)
        self.question_cache[question_hash] = {
            "question": question,
            "answer": answer,
            "source_documents": source_documents,
            "timestamp": datetime.now().isoformat()
        }
        self._save_cache()
    
    def create_conversation_thread(self, thread_id: str = None) -> str:
        """Create a new conversation thread."""
        if thread_id is None:
            thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
        
        if thread_id not in self.conversations:
            self.conversations[thread_id] = {
                "thread_id": thread_id,
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "topic": None
            }
            self._save_conversations()
        
        return thread_id
    
    def add_message(self, thread_id: str, role: str, content: str, sources: List[Dict] = None, metadata: Dict = None):
        """Add a message to a conversation thread."""
        if thread_id not in self.conversations:
            self.create_conversation_thread(thread_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "sources": sources or [],
            "metadata": metadata or {}
        }
        
        self.conversations[thread_id]["messages"].append(message)
        
        # Update topic if it's the first user question
        if role == "user" and not self.conversations[thread_id]["topic"]:
            self.conversations[thread_id]["topic"] = content[:100]  # First 100 chars as topic
        
        self._save_conversations()
    
    def get_thread_history(self, thread_id: str, max_messages: int = 10) -> List[Dict]:
        """Get conversation history for a thread."""
        if thread_id not in self.conversations:
            return []
        
        messages = self.conversations[thread_id]["messages"]
        # Return last N messages
        return messages[-max_messages:] if len(messages) > max_messages else messages
    
    def get_thread_context(self, thread_id: str) -> str:
        """Get formatted context from thread history for prompt."""
        history = self.get_thread_history(thread_id)
        
        if not history:
            return ""
        
        context_parts = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def get_all_threads(self) -> List[Dict]:
        """Get all conversation threads with metadata."""
        threads = []
        for thread_id, thread_data in self.conversations.items():
            topic = thread_data.get("topic")
            if not topic:
                # Try to get topic from first user message
                messages = thread_data.get("messages", [])
                for msg in messages:
                    if msg.get("role") == "user":
                        topic = msg.get("content", "Untitled")[:50]
                        break
                if not topic:
                    topic = "Untitled Conversation"
            
            threads.append({
                "thread_id": thread_id,
                "topic": topic,
                "created_at": thread_data.get("created_at", ""),
                "message_count": len(thread_data.get("messages", []))
            })
        return sorted(threads, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def delete_thread(self, thread_id: str):
        """Delete a conversation thread."""
        if thread_id in self.conversations:
            del self.conversations[thread_id]
            self._save_conversations()

