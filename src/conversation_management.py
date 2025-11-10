"""
Conversation management with memory, caching, and threading.
"""
import json
import os
import hashlib
from typing import Dict, List, Optional
from datetime import datetime
import src.config as config
import uuid
from src.utils.logger import AppLogger

logger = AppLogger(name="conversation_manager")

class ConversationManager:
    """Manages conversation history, caching, and threading."""
    
    def __init__(self, cache_dir: str = "./cache", db: object=None, user_id: str=None):
        """Initialize conversation manager."""
        self.cache_dir = cache_dir
        self.conversations_file = os.path.join(cache_dir, "conversations.json")
        self.cache_file = os.path.join(cache_dir, "question_cache.json")
        self.db = db
        self.user_id = user_id
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load existing data
        if user_id:
            self.conversations = self.db.get_all_conversations_of_user(self.user_id)
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
    
    def set_user(self, user_id):
        self.user_id = user_id
    
    #SQLite
    def create_conversation_thread(self, conversation_id: str = None) -> str:
        """Create a new conversation thread."""
        if conversation_id is None:
            conversation_id = f"CNV_{uuid.uuid4().hex[:12]}"
        
        # if thread_id not in self.conversations:
        #     self.conversations[thread_id] = {
        #         "thread_id": thread_id,
        #         "created_at": datetime.now().isoformat(),
        #         "messages": [],
        #         "topic": None
        #     }
        #     self._save_conversations()
            
        if self.user_id:
            if not any(conv["id"] == conversation_id for conv in self.conversations):
                self.db.create_conversation(conversation_id, "", self.user_id)

        self.conversations = self.db.get_all_conversations_of_user(self.user_id)                
        return conversation_id
    
    # session_manager.get("conversation_manager").cache_answer(
    #     prompt,
    #     result["suggestions"][0] if result["suggestions"] else result.get("answer", ""),
    #     result["source_documents"]
    # )
    
    #SQLite
    def add_message(self, conversation_id: str, sender: str, message: str, sources: List[Dict] = None, metadata: Dict = None, message_id: str=None):
        """Add a message to a conversation thread."""
        if not any(conv["id"] == conversation_id for conv in self.conversations):
            self.create_conversation_thread(conversation_id)
        
        # Store message
        try:
            position = self.db.add_message(conversation_id, sender, message)
            logger.info("Message added!")
        except Exception as e:
            logger.error(f"Failed to add messages: {e}")
        
        # Update topic if it's the first user question
        if sender == "user":
            convo = self.db.get_conversation_of_user(conversation_id, self.user_id)
            if convo and not convo.get("title"):
                self.db.update_title(conversation_id, message[:100])
                logger.info("Title updated!")# First 100 chars as topic
        
        # Refresh cache
        self.conversations = self.db.get_all_conversations_of_user(self.user_id)
        return position
    
    #SQLite
    def get_conversation_history(self, conversation_id: str, max_messages: int = 10) -> List[Dict]:
        """Get conversation history for a thread."""
        conversations = self.db.get_all_conversations_of_user(self.user_id)
        self.conversations = conversations

        valid_conversation_ids = {
            conversation.get("id") for conversation in conversations if conversation.get("id")
        }
        if conversation_id not in valid_conversation_ids:
            return []

        messages = self.db.get_all_messages_from_conversation(conversation_id)
        if len(messages) <= max_messages:
            return messages
        return messages[-max_messages:]
    
    #SQLite
    def get_thread_context(self, conversation_id: str) -> str:
        """Get formatted context from thread history for prompt."""
        history = self.get_conversation_history(conversation_id)
        
        if not history:
            return ""
        
        context_parts = []
        for msg in history:
            role = "User" if msg["sender"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['message']}")
        
        return "\n".join(context_parts)
    
    #SQLite
    def get_all_conversations(self) -> List[Dict]:
        """
        Get all conversation threads with metadata.
        Each thread includes: id, title/topic, created_at, message_count.
        """        
        threads = []
        for thread_data in self.db.get_all_conversations_of_user(self.user_id):
            topic = thread_data.get("title")
            conversation_id = thread_data.get("id")
            if not topic:
                topic = "Untitled Conversation"
                
            threads.append({
                "thread_id": conversation_id,
                "topic": topic,
                "created_at": thread_data.get("created_at"),
                "message_count": self.db.get_count_message_of_conversation(conversation_id)
            })
        return sorted(threads, key=lambda x: x.get("created_at", ""), reverse=True)
    
    #SQLite
    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation thread."""
        if any(conv["conversation_id"] == conversation_id for conv in self.conversations):
            self.db.delete_row("conversations", "conversation_id = ?", (conversation_id,))
            self.conversations = self.db.get_all_conversations_of_user()
    
    # def delete_thread(self, thread_id: str):
    #     """Delete a conversation thread."""
    #     if thread_id in self.conversations:
    #         del self.conversations[thread_id]
    #         self._save_conversations()

def main():
    pass
    
if __name__ == "__main__":
    main()