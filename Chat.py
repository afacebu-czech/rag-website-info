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
from src.conversation_management import ConversationManager
from PIL import Image
import src.config as config
from src.session_management import SessionManager
from typing import Dict
from src.sqlite_manager import SQLiteManager
from src.utils.logger import AppLogger

logger = AppLogger()

VALID_USERNAME = "user"
VALID_PASSWORD = "password123"

db = SQLiteManager()

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
if "session_manager" not in st.session_state:
    st.session_state["session_manager"] = SessionManager(user_id=None)
session_manager = st.session_state["session_manager"]

def check_password(username, password):
    """Simple function to check credentials."""
    return username == VALID_USERNAME and password == VALID_PASSWORD

def login():
    """Renders the login form in the sidebar."""
    st.header("User Login")
    
    if not session_manager.get("authenticated"):
        with st.form("login_form", width=500, border=False):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                status = db.get_user_credentials(username=session_manager.get("username"), password=session_manager.get("password"))
                if status:
                    session_manager.set("authenticated", True)
                    session_manager.set("user_id", status.get("id"))
                    session_manager.set("current_user", status.get("username"))
                    session_manager.get("conversation_manager").set_user(status.get("id"))
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    else:
        # Display the logout button when authenticated
        st.write(f"Welcome, **{VALID_USERNAME}**!")
        if st.button("Logout"):
            session_manager.set("authenticated", False)
            st.info("Logged out.")
            st.rerun()
    

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
    
def input_handler(user_input: Dict[str, any]):
    """Detects what kind of input the user sent (text, image, or both)."""
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
            session_manager.set("pasted_image", True)
            
            # Also check if there's text with the image
            if user_input.get("text"):
                prompt = user_input["text"].strip()
            elif user_input.get("message"):
                prompt = user_input["message"].strip()
                
        elif user_input.get("text"):
            # Text only
            prompt = user_input["text"].strip()
            session_manager.set("pasted_image", False)
            
        elif user_input.get("message"):
            # Text only (alternative key)
            prompt = user_input["message"].strip()
            session_manager.set("pasted_image", False)
            
    elif isinstance(user_input, str):
        # String input (fallback)
        prompt = user_input.strip()
        session_manager.set("pasted_image", False)
        
    if session_manager.get("pasted_image"):
        return uploaded_image, prompt
    else:
        return None, prompt
    
def process_image(uploaded_image):
    # Clear any previous image processing state
    if "pending_inquiry" in session_manager.get_session_snapshot() and "image" in session_manager.get("pending_inquiry"):
        # Only clear if it's a different image
        pass
    
    if session_manager.get("image_processor"):
        # Handle different image input types
        try:
            import io
            
            # Handle dictionary format from multimodal_chat_input
            if isinstance(uploaded_image, dict):
                # Extract image data from dictionary, Try common keys that might contain the image data
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
                    st.image(image, caption="📷 Pasted/Uploaded Image", width=True)
                
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
                                session_manager.stop_processing()
                                st.stop()
                                return
                        
                        # Add to session state for processing
                        pending_inquiry_dict = {
                            "prompt": prompt.strip(),
                            "client_name": client_name,
                            "image": image,
                            "extracted_text": result["extracted_text"]
                        }
                        session_manager.set("pending_inquiry", pending_inquiry_dict)
                        
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
        
def handle_suggestion_selection():
    """Handle saving the selected response suggestion and updating the chat history."""
    selected_option = session_manager.get("selected_response")
    
    if selected_option:
        messages = session_manager.get("messages")
        messages.append({
            "role": "assistant",
            "content": selected_option
        })
        session_manager.set("messages", messages)
        
        # Add to persisten conversation history
        session_manager.get("conversation_manager").add_message(
            conversation_id=session_manager.get("current_thread_id"),
            sender="assistant",
            message=selected_option,
            # sources=suggestions_data.get("sources", [])
        )
        
        session_manager.set("current_suggestions", None)
        session_manager.clear("selected_response")
        session_manager.stop_processing()
    
        logger.info(f"Suggestion saved: {selected_option}")
        
def render_sidebar():
    """Renders all UI components in the sidebar."""
    with st.sidebar:
        if st.button("New Thread", use_container_width=True):
            session_manager.set("current_thread_id", session_manager.get("conversation_manager").create_conversation_thread())
            session_manager.set("messages", [])
            st.rerun()
            
        st.subheader("Conversation Threads")
        threads = session_manager.get("conversation_manager").get_all_conversations(session_manager.get("user_id"))
        if threads:
            thread_options = {}
            for t in threads:
                topic = t.get('topic') or 'Untitled Conversation'
                topic_display = topic.replace("\n", " ")
                topic_display = topic_display[:50] + "..." if len(topic_display) > 50 else topic_display
                msg_count = t.get('message_count', 0)
                thread_options[f"{topic_display} ({msg_count} msgs)"] = t['thread_id']
                
            if thread_options:
                current_index=0
                current_values = list(thread_options.values())
                if session_manager.get("current_thread_id") in current_values:
                    current_index = current_values.index(session_manager.get("current_thread_id"))
                    
                selected_thread_display = st.selectbox(
                    "Switch to thread:",
                    options=list(thread_options.keys()),
                    index=current_index,
                    key="thread_selectbos",
                    help="Select a previous conversation thread"
                )
                
                selected_id = thread_options.get(selected_thread_display)
                if selected_id and selected_id != session_manager.get("current_thread_id"):
                    session_manager.set("current_thread_id", selected_id)
                    # Load thread messages
                    thread_messages = session_manager.get("conversation_manager").get_conversation_history(selected_id)
                    message_dict = [
                        {"role": msg["sender"],
                         "content": msg["message"],
                         "sources":msg.get("sources", [])
                        } for msg in thread_messages
                    ]
                    session_manager.set("messages", message_dict)
                    st.rerun()
                    
def render_document_tab():
    """Renders the Document Upload tab UI."""
    with st.expander("Upload Documents", expanded=True):
        st.header("Upload Documents")
        st.markdown("Upload your business documents (PDF Files) to create a searchable knowledge base for your team.")
        
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type=["pdf"],
            accept_multiple_files=True,
            help="Select one or more PDF files to process"
        )
        
        if uploaded_files:
            st.info(f"{len(uploaded_files)} file(s) selected")
            
            if st.button("Process Documents", type="primary"):
                if process_uploaded_files(uploaded_files):
                    st.success("Documents processed successfully!")
                    st.balloons()
                else:
                    st.error("Failed to process documents")
                    
        if session_manager.get("documents_processed"):
            st.success("Documents are ready for querying!")

def display_chat_messages(messages):
    """Displays all messages in the chat history."""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
        
def render_chat_tab(rag):
    """Renders the Chat Interface tab UI, including the history, and handles input/processing."""
    
    # Check if documents are processed/vectorstore is read
    if not session_manager.get("documents_processed"):
        if rag:
            vs_info = rag.get_vectorstore_info()
            if vs_info["status"] != "initialized" or vs_info.get("document_count", 0) == 0:
                st.warning("Pleas upload and process documents first in the 'Upload Documents' section.")
                return
            
    st.header("Ask Questions")
    st.caption("Get quick, clear answers from your uploaded documents")
    
    # Thread management UI
    col1, col2 = st.columns([3, 1])
    with col1:
        thread_topic = "New conversation"
        if session_manager.get("current_thread_id"):
            threads = session_manager.get("conversation_manager").get_all_conversations(session_manager.get("user_id"))
            for t in threads:
                if t['thread_id'] == session_manager.get("current_thread_id"):
                    thread_topic = t.get('topic', 'Current conversation')
                    thread_topic = thread_topic.replace("\n", " ")
                    if len(thread_topic) > 40:
                        thread_topic = thread_topic[:40] + "..."
                    break
        st.caption(f"Thread: {thread_topic}")
        
    # --- Display Chat History ---
    display_chat_messages(session_manager.get("messages"))

    # --- Display Suggestions (if any) ---
    current_suggestions = session_manager.get("current_suggestions")
    if current_suggestions:
        display_suggestions(current_suggestions, rag)
        return # Stop processing to wait for selection/regeneration
    
    # --- Chat Input ---
    prompt = None
    uploaded_image = None
    user_input = None
    
    if MULTIMODAL_AVAILABLE:
        user_input = multimodal_chat_input(
            placeholder="Type a message or paste an image (Ctrl+V)...",
            accepted_file_types=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
            enable_voice_input=False,
            max_file_size_mb=10,
            key="multimodal_chat_input"
        )
        if user_input:
            uploaded_image, prompt = input_handler(user_input)
        
    else:
        # Fallback to native Streamlit chat_input with files
        try:
            user_input = st.chat_input(
                "Type a message or attach an image...",
                key="main_chat_input",
                accept_file=True,
                file_type=["png", "jpg", "jpeg", "gif", "bmp"]
            )
            
            if user_input:
                if hasattr(user_input, 'files') and user_input.files:
                    uploaded_image = user_input.files[0]
                    session_manager.set("pasted_image", True)
                    prompt = user_input.text if hasattr(user_input, 'text') and user_input.text else ""
                elif hasattr(user_input, 'text') and user_input.text:
                    prompt = user_input.text
                    session_manager.set("pasted_image", False)
                elif isinstance(user_input, str):
                    prmpt = user_input
                    session_manager.set("pasted_image", False)
        except TypeError:
            # Fallback for older Streamlit versions
            col1, col2 = st.columns([5, 1])
            with col1:
                if not session_manager.get("is_processing"):
                    prompt = st.chat_input("Ask a question...", key="main_chat_input")
                else:
                    st.chat_input("Processing...", key="disabled_input", disabled=True)
            with col2:
                uploaded_image = st.file_uploader(
                    "📷",
                    type=["png", "jpg", "jpeg", "gif", "bmp"],
                    help="Paste (Ctrl+V) or upload",
                    key="inquiry_image_fallback",
                    label_visibility="collapsed"
                )
                
    # Start processing only if there is input
    if (uploaded_image is not None or (prompt and len(prompt.strip()) > 0)):
        session_manager.start_processing()
        handle_chat_input( rag, prompt, uploaded_image)

def handle_chat_input(rag, prompt, uploaded_image):
    """Core logic for processing image, handling prompt, generating response suggestions, and rerunning."""
    
    # Image Processing
    if uploaded_image is not None:
        process_image(uploaded_image)
        # Rerun is triggered inside process_image if successful
        return
    
    # Handle Pending Inquiry from successful image processing
    client_name = None
    image_processed = False
    
    if session_manager.get("pending_inquiry"):
        inquiry_data = session_manager.get("pending_inquiry")
        prompt = inquiry_data.get("prompt", "").strip()
        client_name = inquiry_data.get("client_name")
        extracted_text = inquiry_data.get("extracted_text", "").strip()
        image_processed = True
        session_manager.clear("pending_inquiry") # Clear after reading
        
        if not prompt or len(prompt.strip()) < 5:
            if extracted_text and len(extracted_text) > 10:
                prompt = extracted_text
            elif not prompt:
                st.error("Could not extract a valid inquiry from the image.")
                session_manager.stop_processing()
                return
            
    # Final Prompt Check and User Message Display
    if not prompt or len(prompt.strip()) < 3:
        session_manager.stop_processing()
        st.warning("No valid question found. Please try again.")
        return
    
    if not session_manager.get("current_thread_id"):
        session_manager.set("current_thread_id", session_manager.get("conversation_manager").create_conversation_thread())
        
    user_message = prompt
    if client_name:
        user_message = f"Client: {client_name}\n\nInquiry: {prompt}"
        
    session_manager.get("conversation_manager").add_message(session_manager.get("current_thread_id"), "user", user_message)
    
    display_message = prompt
    if client_name:
        display_message = f"**{client_name}** asks: {prompt}"
        
    messages = session_manager.get("messages")
    messages.append({
        "role": "user", "content": display_message
    })
    session_manager.set("messages", messages)
    
    # Display the user message immediately
    with st.chat_message("user"):
        if client_name:
            st.markdown(f"**Client:** {client_name}")
        st.markdown(prompt)
    
    # Generate Response Suggestions
    if rag and rag.qa_chain:
        with st.chat_message("assistant"):
            with st.spinner("Generating response suggestions..."):
                
                regenerate_requested = session_manager.get("regenerate_response", False)
                if regenerate_requested:
                    session_manager.set("regenerate_response", False)
                    st.info("Regenerating fresh response (bypassing cache)...")
                    
                conversation_context = session_manager.get("conversation_manager").get_thread_context(
                    session_manager.get("current_thread_id")
                )
                num_suggestions = 2
                result = None
                
                try:
                    # Attempt primary generation
                    if image_processed:
                        st.info("Generating personalized response suggestions...")
                        
                    result = rag.generate_response_suggestions(
                        question=prompt,
                        client_name=client_name,
                        conversation_context=conversation_context,
                        num_suggestions=num_suggestions
                    )
                    
                    if not result or not result.get("suggestions"):
                        raise Exception("No suggestions generated.")
                except Exception as e:
                    logger.error(f"Error during primary generation: {str(e)}")
                    st.warning("Primary generation failed. Trying fallback method...")
                    
                    try:
                        # Fallback to regular query
                        fallback_result = rag.query(prompt, conversation_context=conversation_context)
                        if fallback_result.get("answer"):
                            result = {
                                "suggestions": [fallback_result["answer"]],
                                "source_documents": fallback_result.get("source_documents", []),
                                "cached": False
                            }
                        else:
                            raise Exception("Fallback also failed.")
                    except Exception as e2:
                        st.error(f"Fallback also failed: {str(e2)}")
                        session_manager.stop_processing()
                        st.stop()
                        return
                    
                # Store and Display Suggestions
                session_manager.set("current_suggestions", {
                    "suggestions": result.get("suggestions", []),
                    "sources": result.get("source_documents", []),
                    "client_name": client_name,
                    "inquiry": prompt
                })
                
                session_manager.stop_processing()
                st.rerun() # Rerun to display suggestions and update the history
                
    else:
        st.error("RAG systems not ready. Please check you configuration.")
        session_manager.stop_processing()
        
def display_suggestions(current_suggestions, rag):
    """Displays the response suggestions and selection mechanism."""
    
    suggestions = current_suggestions["suggestions"]
    client_name = current_suggestions.get("client_name")
    
    st.markdown("### Suggested Responses")
    
    # Regenerate button
    regen_col1, regen_col2 = st.columns([3, 1])
    with regen_col1:
        if client_name:
            st.caption(f"Choose a response to send to **{client_name}**:")
        else:
            st.caption("Choose a response to send to the client:")
    with regen_col2:
        if st.button("Regenerate", key="regenerate_top", use_container_width="True", help="Generate new response variations"):
            session_manager.set("regenerate_response", True)
            session_manager.clear("current_suggestions")
            session_manager.clear("selected_response")
            st.rerun()
            
    # Radio button selection
    st.radio(
        "Choose a suggestion:",
        options=suggestions,
        key="selected_response",
        on_change=handle_suggestion_selection,
        index=None,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Source documents expander
    if current_suggestions["sources"]:
        with st.expander("Reference Documents"):
            for i, source in enumerate(current_suggestions["sources"], 1):
                doc_name = source.get("source", "Document").replace("_", " ").replace("-", " ").title()
                st.markdown(f"**{doc_name}**")
                if source.get("content"):
                    preview = source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                    st.caption(preview)
    
    # Bottom Regenerate button
    st.markdown("---")
    regen_bottom_col1, regen_bottom_col2, regen_bottom_col3 = st.columns([2, 1, 1])
    with regen_bottom_col2:
        if st.button("Regenerate All", key="regenerate_bottom", use_container_width=True, help="Generate completely new response variations"):
            session_manager.set("regenerate_response", True)
            session_manager.clear("current_suggestions")
            session_manager.clear("selected_response")            
            st.rerun()
    
def main():
    """Main application function."""
    title_col, logout_col = st.columns([16, 1])
    with title_col:
        st.title("💼 Business Knowledge Assistant")
        
    st.markdown("**Get instant answers from your company documents**")
    
    
    if session_manager.get("authenticated"):
        st.toast("Logged in successfully!", icon="✅", duration="short")
        with logout_col:
            if st.button("Logout"):
                session_manager.set("authenticated", False)
                session_manager.set("user_id", None)
                session_manager.get("conversation_manager").disconnect_user()
                st.rerun()
        
        rag = initialize_rag_system()
        # Sidebar rendering
        render_sidebar()
        
        # Main content tabs (Rendered consistently to avoid recreation issue)
        tab1, tab2 = st.tabs(["Upload Documents", "Chat with Documents"])
        
        with tab1:
            render_document_tab()
        
        with tab2:
            render_chat_tab(rag)
    else:
        login()

if __name__ == "__main__":
    main()

