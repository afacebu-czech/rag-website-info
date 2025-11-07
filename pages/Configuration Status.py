import streamlit as st
import streamlit as st
import os
import multiprocessing
from pathlib import Path
from src.rag_system import RAGSystem
from conversation_management import ConversationManager
from PIL import Image
import src.config as config

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
if "rag_system" not in st.session_state:
    st.session_state.rag_system = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents_processed" not in st.session_state:
    st.session_state.documents_processed = False
if "conversation_manager" not in st.session_state:
    st.session_state.conversation_manager = ConversationManager()
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None
if "use_cache" not in st.session_state:
    st.session_state.use_cache = True
if "image_processor" not in st.session_state:
    try:
        st.session_state.image_processor = ImageProcessor()
    except Exception as e:
        st.session_state.image_processor = None
if "pasted_image" not in st.session_state:
    st.session_state.pasted_image = False
if "regenerate_response" not in st.session_state:
    st.session_state.regenerate_response = False


def initialize_rag_system():
    """Initialize the RAG system."""
    try:
        if st.session_state.rag_system is None:
            with st.spinner("Initializing RAG system..."):
                st.session_state.rag_system = RAGSystem()
                # Try to load existing vector store
                st.session_state.rag_system.load_vectorstore()
        return st.session_state.rag_system
    except Exception as e:
        st.error(f"Failed to initialize RAG system: {str(e)}")
        st.info("Make sure Ollama is running and DeepSeek R1 8B model is available.")
        return None

def main():
    st.title("⚙️ Configuration Status")
    st.write("This is the configuration status page.")
    
    # System status
    st.subheader("System Status")
    rag = initialize_rag_system()
    if rag:
        vs_info = rag.get_vectorstore_info()
        if vs_info["status"] == "initialized":
            st.success(f"✅ Vector Store: {vs_info['document_count']} chunks")
        else:
            st.warning("⚠️ No documents loaded")
    else:
        st.error("❌ RAG System not initialized")
    
    cols1 = st.columns(3)
    # Model info
    cols1[0].subheader("Model Information")
    cols1[0].info(f"""
                  **LLM:** {config.OLLAMA_MODEL}  
                  **Embeddings:** {config.EMBEDDING_MODEL}  
                  **API:** {config.OLLAMA_BASE_URL}  
                  """)
    # Settings
    cols1[1].subheader("Settings")
    cols1[1].info(f"""
            **Chunk Size:** {config.CHUNK_SIZE}  
            **Top-K:** {config.TOP_K}  
            **Max Tokens:** {config.MAX_TOKENS}  
            **Temperature:** {config.TEMPERATURE}  
            """)
    # Performance Settings
    cols1[2].subheader("Performance")
    cpu_count = multiprocessing.cpu_count()
    cols1[2].info(f"""
                  **CPU Cores:** {cpu_count}  
                  **Parallel Processing:** {'Enabled' if config.PARALLEL_PROCESSING else 'Disabled'}  
                  **Workers:** {config.MAX_WORKERS if config.MAX_WORKERS > 0 else cpu_count}  
                  **Batch Size:** {config.BATCH_SIZE}  
                  **Context Size:** {config.CONTEXT_SIZE}  
                  """)

    # Cache settings
    st.subheader("Memory & Cache")
    st.session_state.use_cache = st.checkbox("Enable Answer Caching", value=st.session_state.use_cache, help="Cache similar questions for faster responses")
        
if __name__ == "__main__":
    main()