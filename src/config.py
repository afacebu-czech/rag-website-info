"""
Configuration settings for the RAG system.
"""
import os
from dotenv import load_dotenv

load_dotenv()

USE_OLLAMA = False

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:70b")

# Gemini Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Embedding Configuration
# Note: DeepSeek R1 8B doesn't support embeddings, so we use a dedicated embedding model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text-v1.5")

# Document Processing Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1500"))  # Larger chunks = fewer chunks to process
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# RAG Configuration
TOP_K = int(os.getenv("TOP_K", "2"))  # Reduced from 4 to 2 for faster responses (fewer chunks to process)
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.6"))  # Balanced for natural business conversations
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "400"))  # Concise responses for business users

# GPU Optimization Configuration (GPU prioritized, CPU as fallback only)
# -1 = use all available GPU layers for max GPU usage (GPU PRIORITIZED)
# 0 = disable GPU, use CPU only (fallback mode)
NUM_GPU_LAYERS = int(os.getenv("NUM_GPU_LAYERS", "-1"))  # Default: -1 (GPU prioritized, use all GPU layers)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1024"))  # Increased batch size = more GPU utilization (512->1024)
CONTEXT_SIZE = int(os.getenv("CONTEXT_SIZE", "8192"))  # Increased context window for better GPU processing (4096->8192)
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "200"))  # Increased batch size for embeddings (100->200)

# CPU Optimization Configuration (for parallel processing)
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))  # Number of CPU threads for parallel processing
PARALLEL_PROCESSING = os.getenv("PARALLEL_PROCESSING", "true").lower() == "true"  # Enable parallel processing
THREAD_COUNT = int(os.getenv("THREAD_COUNT", "0"))  # 0 = use all available CPU threads

# Vector Store Configuration
VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "./database")
PERSIST_DIRECTORY = os.path.join(VECTORSTORE_DIR, "vectorstore")

# File Upload Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "50"))  # MB

# Streamlit Configuration
PAGE_TITLE = "Business Knowledge Assistant"
PAGE_ICON = "💼"

os.environ["USER_AGENT"] = "my-rag-app/1.0"
USER_AGENT = os.environ.get("USER_AGENT")