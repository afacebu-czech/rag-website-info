import streamlit as st
from src.conversation_management import ConversationManager
from src.sqlite_manager import SQLiteManager
import time
from src.config import SESSION_TIMEOUT
from src.utils.logger import AppLogger
from typing import Dict, Any

logger = AppLogger(name="session_management")
class SessionManager:
    """Handles Streamlit session state initialization and management."""
    
    # --- INITIALIZATION ---
    
    def __init__(self, cookies: Any):
        self.cookies = cookies
        self._initialize_sessions()
        
    def _initialize_sessions(self):
        """Initialize all required session variables with safe defaults"""
        if st.session_state.get("_initialized", False):
            return
        
        if "session_token" not in st.session_state:
            st.session_state.session_token = None
        
        if "user_id" not in st.session_state:
            st.session_state.user_id = None
            
        if "current_user" not in st.session_state:
            st.session_state.current_user = None
        
        if "rag_system" not in st.session_state:
            st.session_state.rag_system = None
            
        if "messages" not in st.session_state:
            st.session_state['messages'] = []

        if "documents_processed" not in st.session_state:
            st.session_state.documents_processed = False
            
        if "db" not in st.session_state:
            st.session_state.db = SQLiteManager()

        if "conversation_manager" not in st.session_state:
            st.session_state.conversation_manager = ConversationManager(db=st.session_state.db)

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
        
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
            
        if "cookies" not in st.session_state:
            st.session_state.cookies = self.cookies
        
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
        
    def logged_out(self):
        """Fully reset session state (except cached items)."""
        keys_to_clear = [
            "authenticated"
            "messages",
            "documents",
            "current_thread_id",
            "pasted_image",
            "regenerate_response",
            "is_processing",
            "valid_session"
        ]
        self.delete_cookie()
        
        self._delete_session(token=self.get("session_token"))
        
        token = self.get('session_token')
        if token:
            self._delete_session(token)
        if self.get("session_token"):
            self.clear("session_token")
        if self.get("user_id"):
            self.clear("user_id")
        
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
    
    def write_cookie_once(self, token):
        if self.cookies.get("session_token") != token:
            self.cookies["session_token"] = token
            self.cookies.save()
            
    def delete_cookie(self):
        if self.cookies.get("session_token"):
            self.cookies["session_token"] = ""
            self.cookies.save()
    
    def logged_in(self, status: Dict[str, str]):
        """Set the user_id when logged in"""
        self.set("authenticated", True)
        self.set("user_id", status.get("id"))
        self.set("current_user", status.get("username"))
        
        self.get("conversation_manager").set_user(status.get("id"))
        
        session_token = self.get("db").create_session(status.get("id"))
        self.set("session_token", session_token)
        
        self.write_cookie_once(session_token)
    
    def validate_sessions(self, token: str):
        if token:
            row = self.get('db').find_valid_session_by_token(token)
            if row and int(time.time()) < row["expires_at"]:
                self._refresh_session(token)
                
                self.cookies["session_token"] = token
                self.cookies.save()
                self.set("user_id", row["user_id"])
                return True
            else:
                self.logout_current_session()
                return False

    def logout_current_session(self):
        token = self.get('session_token')
        if token:
            self._delete_session(token)
            
        # clear memory
        self.clear("session_token")
        self.clear("user_id")
        
        # remove cookie
        if "session_token" in self.cookies:
            del self.cookies["session_token"]
            self.cookies.save()
    
    def _refresh_session(self, token: str):
        now = int(time.time())
        new_expires = now + SESSION_TIMEOUT
        self.get("db").update_session_expiry(token, new_expires)
        
    def _delete_session(self, token: str):
        self.get("db").delete_session(token)
        