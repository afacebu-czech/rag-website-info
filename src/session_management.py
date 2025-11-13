import streamlit as st
from src.conversation_management import ConversationManager
from src.sqlite_manager import SQLiteManager
class SessionManager:
    """Handles Streamlit session state initialization and management."""
    
    # --- INITIALIZATION ---
    
    def __init__(self, user_id: str=None):
        self.user_id = user_id
        self._initialize_sessions()
        
    def _initialize_sessions(self):
        """Initialize all required session variables with safe defaults"""
        if st.session_state.get("_initialized", False):
            return
        
        if "user_id" not in st.session_state:
            st.session_state.user_id = self.user_id
        
        if "rag_system" not in st.session_state:
            st.session_state.rag_system = None
            
        if "messages" not in st.session_state:
            st.session_state['messages'] = []

        if "documents_processed" not in st.session_state:
            st.session_state.documents_processed = False
            
        if "db" not in st.session_state:
            st.session_state.db = SQLiteManager()

        if "conversation_manager" not in st.session_state:
            st.session_state.conversation_manager = ConversationManager(db=st.session_state.db, user_id=st.session_state.user_id)

        if "current_thread_id" not in st.session_state:
            st.session_state.current_thread_id = None

        if "use_cache" not in st.session_state:
            st.session_state.use_cache = True

        if "image_processor" not in st.session_state:
            try:
                from src.image_processor import ImageProcessor
                st.session_state.image_processor = ImageProcessor()
            except Exception as e:
                st.warning(f"⚠️ ImageProcessor init failed: {e}")
                st.session_state.image_processor = None

        if "pasted_image" not in st.session_state:
            st.session_state.pasted_image = False

        if "regenerate_response" not in st.session_state:
            st.session_state.regenerate_response = False

        if "is_processing" not in st.session_state:
            st.session_state.is_processing = False
            
        if "pending_query" not in st.session_state:
            st.session_state.pending_query = None
            
        if "pending_inquiry" not in st.session_state:
            st.session_state.pending_inquiry = {}
            
        if "current_suggestions" not in st.session_state:
            st.session_state.current_suggestions = {}
            
        if "is_suggestion_generated" not in st.session_state:
            st.session_state.is_suggestion_generate = False
            
        if "selected_response_idx" not in st.session_state:
            st.session_state.selected_response_idx = None
            
        if "selected_response" not in st.session_state:
            st.session_state.selected_response = None
        
        if "current_tab" not in st.session_state:
            st.session_state.current_tab = "tab1"
        
        st.session_state["_initialized"] = True
    # --- GETTER & SETTER ---
            
    def get(self, key, default=None):
        """Get a session variable safely."""
        return st.session_state.get(key, default)
    
    def set(self, key, value):
        """Set a session variable."""
        st.session_state[key] = value
    
    # --- METHODS ---
    
    def get_session_snapshot(self):
        return st.session_state
    
    def clear(self, key):
        """clear a session variable's value"""
        del st.session_state[key]
        
    def reset_conversation(self):
        """Clear conversation-related states."""
        st.session_state.messages = []
        st.session_state.current_thread_id = None
        st.session_state.regenerate_response = False
        
    def clear_all(self):
        """Fully reset session state (except cached items)."""
        keys_to_clear = [
            "messages",
            "documents",
            "current_thread_id",
            "pasted_image",
            "regenerate_response",
            "is_processing"
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
                
        self._initialize_sessions()
        
    def start_processing(self):
        """Mark the app as busy."""
        st.session_state.is_processing = True
        
    def stop_processing(self):
        """Mark the app as idle."""
        st.session_state.is_processing = False
    
    def is_busy(self):
        """Check if the app is currently processing"""
        return st.session_state.is_processing
    
    def set_user(self, user_id: str):
        """Set the user_id when logged in"""
        if user_id:
            st.session_state.user_id = user_id
            st.session_state.conversation_manager.set_user(user_id)
            return "User logged in successfully."
        return "User failed to logged in"