"""
Streamlit application for the Local RAG System.
"""
import streamlit as st
import os
import tempfile
import uuid
import multiprocessing
from pathlib import Path
from src.rag_system import RAGSystem
from src.document_processor import DocumentProcessor
from conversation_management import ConversationManager
from PIL import Image
import src.config as config
from src.session_management import SessionManager

# Set environment variable to avoid OpenMP warning (needed for EasyOCR/numpy)
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

# Import image processor after setting environment variable
from src.image_processor import ImageProcessor

# Try multimodal component first (supports Ctrl+V paste), fallback to native Streamlit
try:
    from st_chat_input_multimodal import multimodal_chat_input
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False
    multimodal_chat_input = None

# Page configuration
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout="wide"
)

# Initialize session state
session_manager = SessionManager()
session_manager._initialize_sessions()

def initialize_rag_system():
    """Initialize the RAG system."""
    try:
        if session_manager.get("rag_system") is None:
            with st.spinner("Initializing RAG system..."):
                session_manager.set("rag_system", RAGSystem()) 
                # Try to load existing vector store
                session_manager.get("rag_system").load_vectorstore()
        return session_manager.get("rag_system")
    except Exception as e:
        st.error(f"Failed to initialize RAG system: {str(e)}")
        st.info("Make sure Ollama is running and DeepSeek R1 8B model is available.")
        return None


def process_uploaded_files(uploaded_files):
    """Process uploaded PDF files."""
    if not uploaded_files:
        return False
    
    try:
        rag = initialize_rag_system()
        if rag is None:
            return False
        
        # Ensure upload directory exists (use absolute path)
        upload_dir = os.path.abspath(config.UPLOAD_DIR)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded files temporarily
        temp_files = []
        for uploaded_file in uploaded_files:
            # Create temp file in the upload directory
            # Use a unique filename to avoid conflicts
            safe_filename = f"temp_{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
            temp_file_path = os.path.join(upload_dir, safe_filename)
            
            # Write file content
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Verify file was created
            if not os.path.exists(temp_file_path):
                raise Exception(f"Failed to create file: {temp_file_path}")
            
            temp_files.append(temp_file_path)
        
        # Process documents
        with st.spinner(f"Processing {len(temp_files)} document(s)..."):
            rag.process_documents(temp_files)
            session_manager.set("documents_processed", True)
        
        # Clean up temp files (optional - you might want to keep them)
        # for temp_file in temp_files:
        #     if os.path.exists(temp_file):
        #         os.unlink(temp_file)
        
        return True
        
    except Exception as e:
        st.error(f"Error processing documents: {str(e)}")
        return False

def main():
    """Main application function."""
    st.set_page_config(page_title="Business Knowledge Assistant", page_icon="💼")
    st.title("💼 Business Knowledge Assistant")
    st.markdown("**Get instant answers from your company documents**")
    rag = initialize_rag_system()
    
    # Sidebar
    with st.sidebar:
        rag = initialize_rag_system()
        if st.button("🆕 New Thread", use_container_width=True):
                session_manager.set("current_thread_id", session_manager.get("conversation_manager").create_conversation_thread())
                session_manager.set("messages", [])
                st.rerun()
        # Conversation threads
        st.subheader("Conversation Threads")
        threads = session_manager.get("conversation_manager").get_all_threads()
        if threads:
            # Handle None topic values
            thread_options = {}
            for t in threads[:5]:
                topic = t.get('topic') or 'Untitled Conversation'
                topic_display = topic[:50] + "..." if len(topic) > 50 else topic
                msg_count = t.get('message_count', 0)
                thread_options[f"{topic_display} ({msg_count} msgs)"] = t['thread_id']
            
            if thread_options:
                # Find current index
                current_index = 0
                if session_manager.get("current_thread_id"):
                    current_values = list(thread_options.values())
                    if session_manager.get("current_thread_id") in current_values:
                        current_index = current_values.index(session_manager.get("current_thread_id"))
                
                selected_thread = st.selectbox(
                    "Switch to thread:",
                    options=list(thread_options.keys()),
                    index=current_index,
                    help="Select a previous conversation thread"
                )
                if selected_thread:
                    selected_id = thread_options[selected_thread]
                    if selected_id != session_manager.get("current_thread_id"):
                        session_manager.set("current_thread_id", selected_id)
                        # Load thread messages
                        thread_messages = session_manager.get("conversation_manager").get_thread_history(selected_id)
                        message_dict = [
                            {"role": msg["role"], "content": msg["content"], "sources": msg.get("sources", [])}
                            for msg in thread_messages
                        ]
                        session_manager.set("messages", message_dict)
                        st.rerun()
        else:
            st.caption("No previous threads")
        
        # Clear current conversation
        if st.button("🗑️ Clear Current Conversation"):
            session_manager.set("messages", [])
            st.rerun()
    
    # Main content area
    tab1, tab2 = st.tabs(["📄 Upload Documents", "💬 Chat with Documents"])
    
    # Tab 1: Document Upload
    with tab1:
        st.header("Upload Documents")
        st.markdown("Upload your business documents (PDF files) to create a searchable knowledge base for your team.")
        
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            help="Select one or more PDF files to process"
        )
        
        if uploaded_files:
            st.info(f"📎 {len(uploaded_files)} file(s) selected")
            
            if st.button("🔄 Process Documents", type="primary"):
                if process_uploaded_files(uploaded_files):
                    st.success("✅ Documents processed successfully!")
                    st.balloons()
                else:
                    st.error("❌ Failed to process documents")
        
        # Show processed documents
        if session_manager.get("documents_processed"):
            st.success("✅ Documents are ready for querying!")
    
    # Tab 2: Chat Interface (modularized)
    with tab2:
        from src.ui.chat import render_chat_tab
        render_chat_tab(initialize_rag_system, session_manager)


if __name__ == "__main__":
    main()