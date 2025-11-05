"""
Streamlit application for the Local RAG System.
"""
import streamlit as st
import os
import tempfile
import uuid
import multiprocessing
from pathlib import Path
from rag_system import RAGSystem
from document_processor import DocumentProcessor
from conversation_manager import ConversationManager
from PIL import Image
import config

# Set environment variable to avoid OpenMP warning (needed for EasyOCR/numpy)
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

# Import image processor after setting environment variable
from image_processor import ImageProcessor

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
            st.session_state.documents_processed = True
        
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
    st.title("💼 Business Knowledge Assistant")
    st.markdown("**Get instant answers from your company documents**")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model info
        st.subheader("Model Information")
        st.info(f"**LLM:** {config.OLLAMA_MODEL}\n**Embeddings:** {config.EMBEDDING_MODEL}\n**API:** {config.OLLAMA_BASE_URL}")
        
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
        
        # Settings
        st.subheader("Settings")
        st.info(f"**Chunk Size:** {config.CHUNK_SIZE}\n**Top-K:** {config.TOP_K}\n**Max Tokens:** {config.MAX_TOKENS}\n**Temperature:** {config.TEMPERATURE}")
        
        # Performance Settings
        st.subheader("Performance")
        cpu_count = multiprocessing.cpu_count()
        st.info(f"**CPU Cores:** {cpu_count}\n**Parallel Processing:** {'Enabled' if config.PARALLEL_PROCESSING else 'Disabled'}\n**Workers:** {config.MAX_WORKERS if config.MAX_WORKERS > 0 else cpu_count}\n**Batch Size:** {config.BATCH_SIZE}\n**Context Size:** {config.CONTEXT_SIZE}")
        
        # Cache settings
        st.subheader("Memory & Cache")
        st.session_state.use_cache = st.checkbox("Enable Answer Caching", value=st.session_state.use_cache, help="Cache similar questions for faster responses")
        
        # Conversation threads
        st.subheader("Conversation Threads")
        threads = st.session_state.conversation_manager.get_all_threads()
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
                if st.session_state.current_thread_id:
                    current_values = list(thread_options.values())
                    if st.session_state.current_thread_id in current_values:
                        current_index = current_values.index(st.session_state.current_thread_id)
                
                selected_thread = st.selectbox(
                    "Switch to thread:",
                    options=list(thread_options.keys()),
                    index=current_index,
                    help="Select a previous conversation thread"
                )
                if selected_thread:
                    selected_id = thread_options[selected_thread]
                    if selected_id != st.session_state.current_thread_id:
                        st.session_state.current_thread_id = selected_id
                        # Load thread messages
                        thread_messages = st.session_state.conversation_manager.get_thread_history(selected_id)
                        st.session_state.messages = [
                            {"role": msg["role"], "content": msg["content"], "sources": msg.get("sources", [])}
                            for msg in thread_messages
                        ]
                        st.rerun()
        else:
            st.caption("No previous threads")
        
        # Clear current conversation
        if st.button("🗑️ Clear Current Conversation"):
            st.session_state.messages = []
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
        if st.session_state.documents_processed:
            st.success("✅ Documents are ready for querying!")
    
    # Tab 2: Chat Interface
    with tab2:
        st.header("Ask Questions")
        st.caption("Get quick, clear answers from your uploaded documents")
        
        # Check if documents are processed
        if not st.session_state.documents_processed:
            rag = initialize_rag_system()
            if rag:
                vs_info = rag.get_vectorstore_info()
                if vs_info["status"] != "initialized" or vs_info.get("document_count", 0) == 0:
                    st.warning("⚠️ Please upload and process documents first in the 'Upload Documents' tab.")
                    return
        
        # Thread management UI
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.current_thread_id:
                # Get thread topic for display
                threads = st.session_state.conversation_manager.get_all_threads()
                thread_topic = "Current conversation"
                for t in threads:
                    if t['thread_id'] == st.session_state.current_thread_id:
                        thread_topic = t.get('topic', 'Current conversation')
                        if len(thread_topic) > 40:
                            thread_topic = thread_topic[:40] + "..."
                        break
                st.caption(f"💬 Thread: {thread_topic}")
            else:
                st.caption("💬 Thread: New conversation")
        with col2:
            if st.button("🆕 New Thread", use_container_width=True):
                st.session_state.current_thread_id = st.session_state.conversation_manager.create_conversation_thread()
                st.session_state.messages = []
                st.rerun()
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                # Show cached indicator if applicable
                if message.get("cached"):
                    st.caption("💾 From cache")
                st.markdown(message["content"])
                
                # Show source documents if available (business-friendly format)
                if message["role"] == "assistant" and "sources" in message:
                    with st.expander("📄 Reference Documents"):
                        for i, source in enumerate(message["sources"], 1):
                            doc_name = source.get("source", "Document")
                            doc_name = doc_name.replace("_", " ").replace("-", " ").title()
                            st.markdown(f"**{doc_name}**")
                            if source.get("content"):
                                preview = source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                                st.caption(preview)
        
        # Unified chat input that accepts both text and images (like ChatGPT, Messenger)
        # Supports Ctrl+V paste directly in the chat box
        prompt = None
        uploaded_image = None
        
        if MULTIMODAL_AVAILABLE:
            # Use multimodal component - supports direct Ctrl+V paste in chat box
            user_input = multimodal_chat_input(
                placeholder="💬 Type a message or paste an image (Ctrl+V)...",
                accepted_file_types=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
                enable_voice_input=False,
                max_file_size_mb=10,
                key="multimodal_chat_input"
            )
            
            # Process multimodal input - returns Dict[str, Any] with keys: 'text', 'image', 'audio'
            if user_input:
                # Handle different return formats from multimodal_chat_input
                if isinstance(user_input, dict):
                    # Check for image first (pasted or uploaded)
                    # The image can be in different formats: bytes, file-like object, PIL Image, or dict
                    image_data = user_input.get("image") or user_input.get("file") or user_input.get("files")
                    
                    # Handle list of files
                    if isinstance(image_data, list) and len(image_data) > 0:
                        image_data = image_data[0]
                    
                    # If image_data is itself a dict, we'll handle it in the image processing section
                    # Just pass it through - the image processing code will extract the actual data
                    if image_data:
                        uploaded_image = image_data
                        st.session_state.pasted_image = True
                        # Also check if there's text with the image
                        if user_input.get("text"):
                            prompt = user_input["text"].strip()
                        elif user_input.get("message"):
                            prompt = user_input["message"].strip()
                    elif user_input.get("text"):
                        # Text only
                        prompt = user_input["text"].strip()
                        st.session_state.pasted_image = False
                    elif user_input.get("message"):
                        # Text only (alternative key)
                        prompt = user_input["message"].strip()
                        st.session_state.pasted_image = False
                elif isinstance(user_input, str):
                    # String input (fallback)
                    prompt = user_input.strip()
                    st.session_state.pasted_image = False
        else:
            # Fallback: Use native Streamlit chat_input with file attachment
            # Note: Native version may require clicking attachment button, not direct Ctrl+V
            try:
                user_input = st.chat_input(
                    "💬 Type a message or attach an image...",
                    key="main_chat_input",
                    accept_file=True,
                    file_type=["png", "jpg", "jpeg", "gif", "bmp"]
                )
                
                if user_input:
                    # Check if it's a ChatInput object with files (Streamlit 1.43.0+)
                    if hasattr(user_input, 'files') and user_input.files:
                        # Image was attached
                        uploaded_image = user_input.files[0]
                        st.session_state.pasted_image = True
                        if hasattr(user_input, 'text') and user_input.text:
                            prompt = user_input.text
                    elif hasattr(user_input, 'text') and user_input.text:
                        # Text only
                        prompt = user_input.text
                        st.session_state.pasted_image = False
                    elif isinstance(user_input, str):
                        # String input
                        prompt = user_input
                        st.session_state.pasted_image = False
            except TypeError:
                # Older Streamlit version - use regular chat_input with separate uploader
                col1, col2 = st.columns([5, 1])
                with col1:
                    prompt = st.chat_input("💬 Ask a question...", key="main_chat_input")
                with col2:
                    uploaded_image = st.file_uploader(
                        "📷",
                        type=["png", "jpg", "jpeg", "gif", "bmp"],
                        help="Paste (Ctrl+V) or upload",
                        key="inquiry_image_fallback",
                        label_visibility="collapsed"
                    )
        
        # Process image if pasted/uploaded (handles both paste and upload)
        if uploaded_image is not None:
            # Clear any previous image processing state
            if "pending_inquiry" in st.session_state and "image" in st.session_state.pending_inquiry:
                # Only clear if it's a different image
                pass
            
            if st.session_state.image_processor:
                # Handle different image input types
                try:
                    import io
                    
                    # Handle dictionary format from multimodal_chat_input
                    if isinstance(uploaded_image, dict):
                        # Extract image data from dictionary
                        # Try common keys that might contain the image data
                        image_bytes = None
                        
                        # Check for Streamlit UploadedFile object in dict
                        if 'type' in uploaded_image and uploaded_image.get('type') == 'image':
                            # Handle image type from multimodal component
                            image_bytes = uploaded_image.get('content') or uploaded_image.get('data')
                        
                        # Try common keys
                        if not image_bytes:
                            for key in ['data', 'content', 'bytes', 'file', 'image']:
                                if key in uploaded_image:
                                    image_bytes = uploaded_image[key]
                                    break
                        
                        # If we found bytes, convert to PIL Image
                        if image_bytes:
                            if isinstance(image_bytes, bytes):
                                image = Image.open(io.BytesIO(image_bytes))
                            elif hasattr(image_bytes, 'read'):
                                # It's a file-like object
                                image = Image.open(image_bytes)
                            elif isinstance(image_bytes, Image.Image):
                                # Already a PIL Image
                                image = image_bytes
                            else:
                                # Try to convert to bytes if it's a string (base64 or data URI)
                                import base64
                                if isinstance(image_bytes, str):
                                    # Check if it's a data URI (data:image/png;base64,...)
                                    if image_bytes.startswith('data:image/'):
                                        # Parse data URI format: data:image/png;base64,<base64_data>
                                        try:
                                            # Extract base64 data from data URI
                                            header, encoded = image_bytes.split(',', 1)
                                            # Extract file type from header (e.g., image/png)
                                            file_type = header.split(';')[0].split('/')[1]  # Extract 'png' from 'data:image/png'
                                            # Decode base64
                                            image_data = base64.b64decode(encoded)
                                            image = Image.open(io.BytesIO(image_data))
                                        except Exception as e:
                                            raise ValueError(f"Failed to parse data URI: {str(e)}")
                                    else:
                                        # Try decoding as base64 string
                                        try:
                                            image_data = base64.b64decode(image_bytes)
                                            image = Image.open(io.BytesIO(image_data))
                                        except Exception:
                                            # Not base64, try opening as file path
                                            image = Image.open(image_bytes)
                                else:
                                    # Debug: show what we got
                                    st.error(f"Debug: Image dict keys: {list(uploaded_image.keys())}")
                                    st.error(f"Debug: Image data type: {type(image_bytes)}")
                                    raise ValueError(f"Unsupported image data format in dict: {type(image_bytes)}")
                        else:
                            # Debug: show dictionary structure
                            st.error(f"Debug: Could not find image data. Dictionary keys: {list(uploaded_image.keys())}")
                            st.error(f"Debug: Dictionary content preview: {str(uploaded_image)[:200]}")
                            raise ValueError(f"Could not find image data in dictionary. Keys: {list(uploaded_image.keys())}")
                    elif hasattr(uploaded_image, 'read'):
                        # It's a file-like object (from file_uploader or native Streamlit)
                        image = Image.open(uploaded_image)
                    elif isinstance(uploaded_image, bytes):
                        # It's bytes from multimodal component
                        image = Image.open(io.BytesIO(uploaded_image))
                    elif isinstance(uploaded_image, str):
                        # Handle string input (could be data URI or file path)
                        import base64
                        if uploaded_image.startswith('data:image/'):
                            # Parse data URI format: data:image/png;base64,<base64_data>
                            try:
                                header, encoded = uploaded_image.split(',', 1)
                                # Extract file type from header (e.g., image/png -> png)
                                file_type = header.split(';')[0].split('/')[1]
                                # Decode base64
                                image_data = base64.b64decode(encoded)
                                image = Image.open(io.BytesIO(image_data))
                            except Exception as e:
                                raise ValueError(f"Failed to parse data URI: {str(e)}")
                        else:
                            # Try opening as file path
                            image = Image.open(uploaded_image)
                    else:
                        # Try to open directly (file path or PIL Image)
                        image = Image.open(uploaded_image)
                    
                    with st.spinner("📖 Reading image and extracting text..."):
                        # Display uploaded image in a nice container
                        st.markdown("---")
                        img_col1, img_col2 = st.columns([2, 3])
                        with img_col1:
                            st.image(image, caption="📷 Pasted/Uploaded Image", use_container_width=True)
                        
                        with img_col2:
                            # Process image
                            result = st.session_state.image_processor.process_image(image)
                            
                            if result["success"]:
                                # Show extracted information in a compact, friendly format
                                st.success("✅ Image processed successfully!")
                                
                                if result["client_name"]:
                                    st.info(f"👤 **Client:** {result['client_name']}")
                                else:
                                    st.caption("ℹ️ Client name not detected - responses will use generic greeting")
                                
                                if result["inquiry"]:
                                    st.markdown(f"**📝 Inquiry:**")
                                    st.write(result["inquiry"])
                                
                                # Show multiple questions if detected
                                if result.get("has_multiple_questions") and result.get("questions"):
                                    st.success(f"✅ Detected {len(result['questions'])} questions!")
                                    with st.expander(f"📋 View {len(result['questions'])} Individual Questions"):
                                        for i, q in enumerate(result["questions"], 1):
                                            st.markdown(f"**{i}.** {q}")
                                
                                # Show full extracted text in expander
                                with st.expander("📄 View Full Extracted Text"):
                                    st.text_area("", result["extracted_text"], height=150, label_visibility="collapsed", key="extracted_text_display")
                                
                                # Use extracted inquiry as prompt
                                prompt = result["inquiry"]
                                client_name = result["client_name"]
                                
                                # Validate that we have an inquiry
                                if not prompt or len(prompt.strip()) < 5:
                                    # If inquiry is too short or empty, use the full extracted text
                                    if result["extracted_text"] and len(result["extracted_text"].strip()) > 10:
                                        prompt = result["extracted_text"].strip()
                                        st.warning("⚠️ No clear inquiry detected. Using full extracted text as inquiry.")
                                    else:
                                        st.error("❌ Could not extract a valid inquiry from the image. Please ensure the text is clear and readable.")
                                        st.stop()
                                        return
                                
                                # Add to session state for processing
                                st.session_state.pending_inquiry = {
                                    "prompt": prompt.strip(),
                                    "client_name": client_name,
                                    "image": image,
                                    "extracted_text": result["extracted_text"]
                                }
                                
                                st.balloons()  # Celebration for successful processing!
                                st.success("🚀 Ready to generate response suggestions! Processing automatically...")
                                
                                # Auto-process after a brief moment
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to process image: {result.get('error', 'Unknown error')}")
                                st.info("💡 Try a clearer image or check that the text is readable")
                except Exception as e:
                    st.error(f"❌ Error processing image: {str(e)}")
                    st.info("💡 Make sure the image format is supported (PNG, JPG, JPEG, GIF, BMP)")
            else:
                st.error("⚠️ Image processing not available. Please install OCR dependencies: `pip install easyocr pillow`")
        
        # Process text prompt or pending inquiry
        if prompt or st.session_state.get("pending_inquiry"):
            # Handle pending inquiry from image
            client_name = None
            image_processed = False
            if st.session_state.get("pending_inquiry"):
                inquiry_data = st.session_state.pending_inquiry
                prompt = inquiry_data.get("prompt", "").strip()
                client_name = inquiry_data.get("client_name")
                extracted_text = inquiry_data.get("extracted_text", "").strip()
                image_processed = True
                
                # If prompt is empty or too short, use extracted text
                if not prompt or len(prompt.strip()) < 5:
                    if extracted_text and len(extracted_text) > 10:
                        prompt = extracted_text
                        st.warning("ℹ️ Using full extracted text as inquiry (no clear question detected).")
                    elif prompt:
                        # Keep the prompt even if short
                        pass
                    else:
                        st.error("❌ Could not extract a valid inquiry from the image.")
                        st.stop()
                        return
                
                # Clear pending inquiry
                del st.session_state.pending_inquiry
            
            # Ensure we have a prompt
            if not prompt or len(prompt.strip()) < 3:
                st.warning("⚠️ No valid question found. Please try again.")
                st.stop()
                return
            
            # Initialize or get current thread
            if not st.session_state.current_thread_id:
                st.session_state.current_thread_id = st.session_state.conversation_manager.create_conversation_thread()
            
            # Format user message with client name if available
            user_message = prompt
            if client_name:
                user_message = f"Client: {client_name}\n\nInquiry: {prompt}"
            
            # Add user message to thread
            st.session_state.conversation_manager.add_message(
                st.session_state.current_thread_id,
                "user",
                user_message
            )
            
            # Add user message to display
            display_message = prompt
            if client_name:
                display_message = f"**{client_name}** asks: {prompt}"
            st.session_state.messages.append({"role": "user", "content": display_message})
            
            # Display user message
            with st.chat_message("user"):
                if client_name:
                    st.markdown(f"**Client:** {client_name}")
                st.markdown(prompt)
            
            # Get response suggestions from RAG system
            rag = initialize_rag_system()
            if rag and rag.qa_chain:
                with st.chat_message("assistant"):
                    with st.spinner("Generating response suggestions..."):
                        try:
                            # Debug: Show what we're processing
                            if image_processed:
                                st.caption(f"Processing inquiry: {prompt[:100]}...")
                            
                            # Check if regeneration was requested (bypass cache)
                            regenerate_requested = st.session_state.get("regenerate_response", False)
                            if regenerate_requested:
                                # Clear the regeneration flag
                                st.session_state.regenerate_response = False
                                st.info("🔄 Regenerating fresh response (bypassing cache)...")
                            
                            # Check cache first if enabled (but skip if regeneration requested)
                            cached_result = None
                            if st.session_state.use_cache and not regenerate_requested:
                                cached_result = st.session_state.conversation_manager.find_similar_question(prompt)
                                if cached_result and cached_result.get("similarity", 0) >= 0.9:
                                    st.info("💾 Using cached answer (similar question found)")
                                    # Show option to regenerate even if cached
                                    col1, col2 = st.columns([3, 1])
                                    with col2:
                                        if st.button("🔄 Regenerate", key="regenerate_cached", use_container_width=True):
                                            st.session_state.regenerate_response = True
                                            st.rerun()
                                    result = {
                                        "suggestions": [cached_result["answer"]],
                                        "source_documents": cached_result.get("source_documents", []),
                                        "cached": True,
                                        "original_question": cached_result.get("original_question")
                                    }
                                else:
                                    # Get conversation context
                                    conversation_context = st.session_state.conversation_manager.get_thread_context(
                                        st.session_state.current_thread_id
                                    )
                                    
                                    # Generate multiple response suggestions
                                    num_suggestions = 2  # Default to 2, can be configured
                                    
                                    # Show processing message
                                    if image_processed:
                                        st.info("🎯 Generating personalized response suggestions based on the client inquiry...")
                                    
                                    try:
                                        result = rag.generate_response_suggestions(
                                            question=prompt,
                                            client_name=client_name,
                                            conversation_context=conversation_context,
                                            num_suggestions=num_suggestions
                                        )
                                        
                                        # Validate result
                                        if not result or not result.get("suggestions"):
                                            st.warning("⚠️ No suggestions generated. Trying fallback method...")
                                            # Fallback to regular query
                                            fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                            if fallback_result.get("answer"):
                                                result = {
                                                    "suggestions": [fallback_result["answer"]],
                                                    "source_documents": fallback_result.get("source_documents", []),
                                                    "cached": False
                                                }
                                            else:
                                                raise Exception("Could not generate any response")
                                        
                                        # Cache the answer
                                        st.session_state.conversation_manager.cache_answer(
                                            prompt,
                                            result["suggestions"][0] if result["suggestions"] else result.get("answer", ""),
                                            result["source_documents"]
                                        )
                                        result["cached"] = False
                                    except Exception as e:
                                        st.error(f"❌ Error generating responses: {str(e)}")
                                        st.info("🔄 Trying fallback response generation...")
                                        try:
                                            fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                            if fallback_result.get("answer"):
                                                result = {
                                                    "suggestions": [fallback_result["answer"]],
                                                    "source_documents": fallback_result.get("source_documents", []),
                                                    "cached": False
                                                }
                                            else:
                                                raise Exception("Fallback also failed")
                                        except Exception as e2:
                                            st.error(f"❌ Fallback also failed: {str(e2)}")
                                            st.stop()
                                            return
                            else:
                                # Get conversation context
                                conversation_context = st.session_state.conversation_manager.get_thread_context(
                                    st.session_state.current_thread_id
                                )
                                
                                # Generate multiple response suggestions
                                num_suggestions = 2  # Default to 2, can be configured
                                
                                # Show processing message
                                if image_processed:
                                    st.info("🎯 Generating personalized response suggestions based on the client inquiry...")
                                
                                try:
                                    result = rag.generate_response_suggestions(
                                        question=prompt,
                                        client_name=client_name,
                                        conversation_context=conversation_context,
                                        num_suggestions=num_suggestions
                                    )
                                    
                                    # Validate result
                                    if not result or not result.get("suggestions"):
                                        st.warning("⚠️ No suggestions generated. Trying fallback method...")
                                        # Fallback to regular query
                                        fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                        if fallback_result.get("answer"):
                                            result = {
                                                "suggestions": [fallback_result["answer"]],
                                                "source_documents": fallback_result.get("source_documents", []),
                                                "cached": False
                                            }
                                        else:
                                            raise Exception("Could not generate any response")
                                    
                                    result["cached"] = False
                                except Exception as e:
                                    st.error(f"❌ Error generating responses: {str(e)}")
                                    st.info("🔄 Trying fallback response generation...")
                                    try:
                                        fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                        if fallback_result.get("answer"):
                                            result = {
                                                "suggestions": [fallback_result["answer"]],
                                                "source_documents": fallback_result.get("source_documents", []),
                                                "cached": False
                                            }
                                        else:
                                            raise Exception("Fallback also failed")
                                    except Exception as e2:
                                        st.error(f"❌ Fallback also failed: {str(e2)}")
                                        st.stop()
                                        return
                            
                            # Display response suggestions with selection buttons
                            suggestions = result.get("suggestions", [])
                            
                            # Validate that we have suggestions
                            if not suggestions or len(suggestions) == 0:
                                st.error("❌ No response suggestions generated. This might be due to:")
                                st.markdown("- No relevant information found in documents")
                                st.markdown("- The inquiry could not be processed")
                                st.markdown("- RAG system error")
                                
                                # Try fallback to regular query
                                try:
                                    st.info("🔄 Trying fallback response generation...")
                                    conversation_context = st.session_state.conversation_manager.get_thread_context(
                                        st.session_state.current_thread_id
                                    )
                                    fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                    if fallback_result.get("answer"):
                                        st.markdown("**Response:**")
                                        st.markdown(fallback_result["answer"])
                                        
                                        # Add to conversation
                                        st.session_state.conversation_manager.add_message(
                                            st.session_state.current_thread_id,
                                            "assistant",
                                            fallback_result["answer"],
                                            sources=fallback_result.get("source_documents", [])
                                        )
                                        st.session_state.messages.append({
                                            "role": "assistant",
                                            "content": fallback_result["answer"],
                                            "sources": fallback_result.get("source_documents", [])
                                        })
                                    else:
                                        st.error("❌ Could not generate a response. Please check your documents and try again.")
                                except Exception as e:
                                    st.error(f"❌ Error generating response: {str(e)}")
                                st.stop()
                                return
                            
                            st.markdown("### 💬 Suggested Responses")
                            
                            # Add regenerate button at the top
                            regen_col1, regen_col2 = st.columns([3, 1])
                            with regen_col1:
                                if client_name:
                                    st.caption(f"Choose a response to send to **{client_name}**:")
                                else:
                                    st.caption("Choose a response to send to the client:")
                            with regen_col2:
                                if st.button("🔄 Regenerate", key="regenerate_top", use_container_width=True, help="Generate new response variations"):
                                    st.session_state.regenerate_response = True
                                    st.rerun()
                            
                            selected_response = None
                            
                            # Store suggestions in session state for selection
                            st.session_state.current_suggestions = {
                                "suggestions": suggestions,
                                "sources": result["source_documents"],
                                "client_name": client_name,
                                "inquiry": prompt
                            }
                            
                            # Display each suggestion with a select button
                            for idx, suggestion in enumerate(suggestions, 1):
                                with st.container():
                                    col1, col2 = st.columns([4, 1])
                                    with col1:
                                        st.markdown(f"**Option {idx}:**")
                                        st.markdown(suggestion)
                                    with col2:
                                        if st.button("📋 Use This", key=f"select_{idx}_{len(st.session_state.messages)}", use_container_width=True):
                                            st.session_state.selected_response_idx = idx
                                            st.session_state.selected_response = suggestion
                                            st.rerun()
                                    
                                    if idx < len(suggestions):
                                        st.divider()
                            
                            # Add regenerate button at the bottom
                            st.markdown("---")
                            regen_bottom_col1, regen_bottom_col2, regen_bottom_col3 = st.columns([2, 1, 1])
                            with regen_bottom_col2:
                                if st.button("🔄 Regenerate All", key="regenerate_bottom", use_container_width=True, help="Generate completely new response variations (bypasses cache)"):
                                    st.session_state.regenerate_response = True
                                    st.rerun()
                            
                            # Check if a response was selected (from previous interaction)
                            if st.session_state.get("selected_response") and st.session_state.get("selected_response_idx"):
                                selected_response = st.session_state.selected_response
                                selected_idx = st.session_state.selected_response_idx
                                
                                # Get stored suggestions data
                                stored_data = st.session_state.get("current_suggestions", {})
                                
                                # Add selected response to conversation
                                st.session_state.conversation_manager.add_message(
                                    st.session_state.current_thread_id,
                                    "assistant",
                                    selected_response,
                                    sources=stored_data.get("sources", result["source_documents"])
                                )
                                
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": f"**Selected Response {selected_idx}:**\n\n{selected_response}",
                                    "sources": stored_data.get("sources", result["source_documents"]),
                                    "suggestions": stored_data.get("suggestions", suggestions),
                                    "selected": selected_idx
                                })
                                
                                # Clear selection state
                                del st.session_state.selected_response
                                del st.session_state.selected_response_idx
                                if "current_suggestions" in st.session_state:
                                    del st.session_state.current_suggestions
                                
                                st.success(f"✅ Response {selected_idx} selected and saved!")
                                st.rerun()
                            
                            # Show source documents
                            if result["source_documents"]:
                                with st.expander("📄 Reference Documents"):
                                    for i, source in enumerate(result["source_documents"], 1):
                                        doc_name = source.get("source", "Document")
                                        doc_name = doc_name.replace("_", " ").replace("-", " ").title()
                                        st.markdown(f"**{doc_name}**")
                                        if source.get("content"):
                                            preview = source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                                            st.caption(preview)
                            
                            
                        except Exception as e:
                            error_msg = f"Error generating suggestions: {str(e)}"
                            st.error(error_msg)
                            # Fallback to regular query
                            try:
                                conversation_context = st.session_state.conversation_manager.get_thread_context(
                                    st.session_state.current_thread_id
                                )
                                result = rag.query(prompt, conversation_context=conversation_context)
                                st.markdown(result["answer"])
                                
                                st.session_state.conversation_manager.add_message(
                                    st.session_state.current_thread_id,
                                    "assistant",
                                    result["answer"],
                                    sources=result["source_documents"]
                                )
                                
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": result["answer"],
                                    "sources": result["source_documents"]
                                })
                            except Exception as e2:
                                st.error(f"Error: {str(e2)}")
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": f"Error: {str(e2)}"
                                })
            else:
                st.error("RAG system not ready. Please check your configuration.")


if __name__ == "__main__":
    main()

