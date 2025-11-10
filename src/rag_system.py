"""
RAG system implementation using LangChain, Ollama, and DeepSeek R1 8B.
"""
USE_OLLAMA=True

import os
from typing import List, Optional, Dict
from langchain_ollama import OllamaLLM, OllamaEmbeddings
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to community version
    from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import src.config as config
from .document_processor import DocumentProcessor
import multiprocessing
from .utils.prompt_templates import PromptTemplates
from src.vectorstore_manager import VectorstoreManager
if not USE_OLLAMA:
    from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.logger import AppLogger

logger = AppLogger(name="conversation_manager")

class RAGSystem:
    """RAG system for querying documents using DeepSeek R1 8B."""
    
    def __init__(self):
        """Initialize the RAG system."""
        self.llm = None
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.qa_chain = None
        self.prompt_templates = PromptTemplates()
        self.document_processor = DocumentProcessor()
        self.vectorstore_manager = None
        
        # Initialize LLM and embeddings
        self._initialize_llm()
        self._initialize_embeddings()
        
        # Initialize VectorstoreManager
        self.vectorstore_manager = VectorstoreManager(self.embeddings)
    
    def _initialize_llm(self):
        """Initialize the Ollama LLM (DeepSeek R1 8B) with GPU prioritized, CPU as fallback only."""
        if USE_OLLAMA:
            try:
                # PRIORITY 1: Configure for GPU usage first
                # num_gpu=-1 uses all available GPU layers for maximum GPU usage
                # OllamaLLM accepts these parameters directly or via kwargs
                llm_params = {
                    "model": config.OLLAMA_MODEL,
                    "base_url": config.OLLAMA_BASE_URL,
                    "temperature": config.TEMPERATURE,
                    "num_predict": config.MAX_TOKENS,
                }
                
                # ALWAYS prioritize GPU - set GPU layers first
                # Only configure CPU if GPU is explicitly disabled
                if config.NUM_GPU_LAYERS != 0:
                    # GPU mode: Set GPU layers for maximum GPU utilization
                    llm_params["num_gpu"] = config.NUM_GPU_LAYERS
                    print(f"🚀 GPU mode: Using {config.NUM_GPU_LAYERS} GPU layers (all available)")
                else:
                    # Only if GPU is explicitly disabled (num_gpu=0), optimize CPU
                    print("⚠️ GPU disabled, using CPU mode")
                
                # GPU-optimized parameters (only meaningful when GPU is enabled)
                if hasattr(config, 'CONTEXT_SIZE') and config.CONTEXT_SIZE:
                    llm_params["num_ctx"] = config.CONTEXT_SIZE
                if hasattr(config, 'BATCH_SIZE') and config.BATCH_SIZE:
                    llm_params["num_batch"] = config.BATCH_SIZE
                
                # CPU threading: Only configure if GPU is disabled or as fallback
                # When GPU is enabled, CPU threads are used for non-GPU operations
                if hasattr(config, 'THREAD_COUNT'):
                    if config.THREAD_COUNT > 0:
                        llm_params["num_thread"] = config.THREAD_COUNT
                    elif config.THREAD_COUNT == 0:
                        # Use all available CPU threads for CPU operations
                        llm_params["num_thread"] = multiprocessing.cpu_count()
                
                self.llm = OllamaLLM(**llm_params)
                
                # Log GPU/CPU configuration
                if config.NUM_GPU_LAYERS != 0:
                    gpu_info = f"GPU layers: {config.NUM_GPU_LAYERS} (prioritized)"
                    cpu_info = f"CPU threads: {llm_params.get('num_thread', 'auto')} (fallback)"
                else:
                    gpu_info = "GPU: disabled"
                    cpu_info = f"CPU threads: {llm_params.get('num_thread', 'auto')} (primary)"
                
                print(f"✅ LLM initialized: {config.OLLAMA_MODEL} ({gpu_info}, {cpu_info}, Context: {config.CONTEXT_SIZE}, Batch: {config.BATCH_SIZE})")
            except Exception as e:
                raise Exception(f"Failed to initialize LLM: {str(e)}")
        else:
            llm = ChatGoogleGenerativeAI(
                model=config.GEMINI_MODEL,
                temperature=0,
                max_tokens=None,
                timeout=None
            )
    
    def _initialize_embeddings(self):
        """Initialize Ollama embeddings with GPU prioritized, CPU as fallback only."""
        try:
            embedding_params = {
                "model": config.EMBEDDING_MODEL,
                "base_url": config.OLLAMA_BASE_URL,
            }
            
            # PRIORITY 1: ALWAYS try GPU first for embeddings
            # Embeddings benefit greatly from GPU acceleration
            if hasattr(config, 'NUM_GPU_LAYERS') and config.NUM_GPU_LAYERS != 0:
                embedding_params["num_gpu"] = config.NUM_GPU_LAYERS
                print(f"🚀 Embeddings GPU mode: Using {config.NUM_GPU_LAYERS} GPU layers (prioritized)")
            else:
                print("⚠️ Embeddings GPU disabled, using CPU mode")
            
            self.embeddings = OllamaEmbeddings(**embedding_params)
            
            # Log GPU/CPU configuration
            if hasattr(config, 'NUM_GPU_LAYERS') and config.NUM_GPU_LAYERS != 0:
                gpu_info = f"GPU layers: {config.NUM_GPU_LAYERS} (prioritized)"
            else:
                gpu_info = "GPU: disabled (CPU fallback)"
            
            print(f"✅ Embeddings initialized: {config.EMBEDDING_MODEL} ({gpu_info})")
        except Exception as e:
            raise Exception(f"Failed to initialize embeddings: {str(e)}")
        
    def process_documents(self, file_paths: List[str]):
        """Process documents and create vector store"""
        documents = self.document_processor.process_multiple_pdfs(file_paths)
        if not documents:
            raise ValueError("No documents were successfully processed")
        
        # Build or update the vector store
        self.vectorstore_manager.create_vectorstore(documents, persist=True)
        # Sync local handles
        self.vectorstore = self.vectorstore_manager.vectorstore
        self.retriever = self.vectorstore_manager.retriever
        # Create QA chain now that retriever is ready
        self._create_qa_chain()
    
    def _create_qa_chain(self):
        """Create the QA chain using LCEL (LangChain Expression Language)."""
        # Business-friendly prompt - personalized, clear, no technical jargon with context awareness
        prompt_template = self.prompt_templates.qa_prompt_template()

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Format documents function - limit context length and filter technical metadata
        def format_docs(docs):
            # Limit each chunk to 800 chars and join with separators
            formatted = []
            max_chars = 800  # Limit per chunk for faster processing
            for doc in docs:
                content = doc.page_content[:max_chars]
                # Remove any code-like patterns or technical references
                # Keep only business-relevant content
                formatted.append(content)
            return "\n\n".join(formatted)
        
        # Store format_docs for use in query method
        self._format_docs = format_docs
        
        # Create the chain using LCEL (for backward compatibility, though we override query method)
        # Retrieve documents -> format -> prompt -> LLM -> parse
        self.qa_chain = (
            {
                "context": self.retriever | format_docs,
                "question": RunnablePassthrough(),
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        # Store retriever separately for source documents
        self._retriever = self.retriever
    
    def generate_response_suggestions(self, question: str, client_name: str = None, conversation_context: str = "", num_suggestions: int = 2) -> Dict[str, any]:
        """
        Generate multiple response suggestions for a client inquiry.
        
        Args:
            question: Client's inquiry/question
            client_name: Name of the client (for personalization)
            conversation_context: Previous conversation context
            num_suggestions: Number of response suggestions to generate (default: 2)
            
        Returns:
            Dictionary with multiple answer suggestions and source documents
        """
        if not self.qa_chain:
            raise ValueError("Vector store not initialized. Please process documents first.")
        
        try:
            logger.info(f"[RAG] Generating {num_suggestions} suggestions for: {question[:80]}")
            # Retrieve source documents first
            source_docs = self._retriever.invoke(question)
            
            # Format context
            formatted_context = self._format_docs(source_docs)
            
            # Format conversation context
            conv_context_text = f"Previous conversation:\n{conversation_context}\n" if conversation_context else ""
            
            # Build personalized prompt for multiple response suggestions
            client_greeting = f"Dear {client_name}," if client_name else "Hello,"
            
            suggestions_prompt_template = self.prompt_templates.suggestion_prompt_template(num_suggestions, client_name, conv_context_text, client_greeting)
            
            # Build the full prompt
            full_prompt = suggestions_prompt_template.format(
                context=formatted_context,
                question=question
            )
            
            # Get answer from LLM
            try:
                answer_text = self.llm.invoke(full_prompt)
                
                # Validate response
                if not answer_text or len(str(answer_text).strip()) < 10:
                    raise Exception("LLM returned empty or very short response")
                
            except Exception as e:
                raise Exception(f"Error getting response from LLM: {str(e)}")
            
            # Parse multiple responses
            try:
                suggestions = self._parse_response_suggestions(answer_text, num_suggestions)
                
                # If parsing failed, try to extract at least one response
                if not suggestions or len(suggestions) == 0:
                    # Try to extract any response from the raw text
                    answer_str = str(answer_text).strip()
                    if len(answer_str) > 20:
                        # Use the full answer as a single suggestion
                        suggestions = [answer_str]
                    else:
                        raise Exception("Could not parse any valid responses from LLM output")
            except Exception as e:
                raise Exception(f"Error parsing response suggestions: {str(e)}")
            
            # Filter source documents
            filtered_sources = []
            for doc in source_docs:
                source_name = doc.metadata.get("source", "Document")
                if "/" in source_name or "\\" in source_name:
                    source_name = source_name.split("/")[-1].split("\\")[-1]
                if "." in source_name:
                    source_name = source_name.rsplit(".", 1)[0]
                
                content = doc.page_content[:400] + "..." if len(doc.page_content) > 400 else doc.page_content
                
                clean_metadata = {}
                if "total_pages" in doc.metadata:
                    clean_metadata["pages"] = doc.metadata.get("total_pages", "")
                
                filtered_sources.append({
                    "content": content,
                    "source": source_name,
                    "metadata": clean_metadata
                })
            
            return {
                "suggestions": suggestions,
                "source_documents": filtered_sources,
                "client_name": client_name,
                "inquiry": question
            }
        except Exception as e:
            raise Exception(f"Error generating response suggestions: {str(e)}")
    
    def _parse_response_suggestions(self, text: str, num_suggestions: int) -> list:
        """Parse multiple response suggestions from LLM output."""
        import re
        
        suggestions = []
        
        # Try to find numbered responses
        pattern = r"(?:Response\s+)?(\d+)[:.\-\s]+(.*?)(?=(?:Response\s+)?\d+[:.\-\s]+|$)"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if matches:
            for num, content in matches:
                content = content.strip()
                if content and len(content) > 20:  # Valid response
                    suggestions.append(content)
        
        # If parsing failed, split by common patterns
        if len(suggestions) < num_suggestions:
            # Try splitting by numbered lists or paragraphs
            parts = re.split(r'\n\s*\n|\n(?=\d+[\.\)])', text)
            for part in parts:
                part = part.strip()
                # Remove "Response X:" prefix if present
                part = re.sub(r'^(?:Response\s+)?\d+[:.\-\s]+', '', part, flags=re.IGNORECASE).strip()
                if part and len(part) > 20 and part not in suggestions:
                    suggestions.append(part)
                    if len(suggestions) >= num_suggestions:
                        break
        
        # If still not enough, split the text into chunks
        if len(suggestions) < num_suggestions:
            # Use the full text as one suggestion, or split it
            if len(suggestions) == 0:
                # Split text into roughly equal parts
                words = text.split()
                chunk_size = len(words) // num_suggestions
                for i in range(num_suggestions):
                    start = i * chunk_size
                    end = start + chunk_size if i < num_suggestions - 1 else len(words)
                    chunk = " ".join(words[start:end])
                    if chunk.strip():
                        suggestions.append(chunk.strip())
        
        # Ensure we have at least the requested number
        while len(suggestions) < num_suggestions:
            suggestions.append(suggestions[-1] if suggestions else "I understand your inquiry and will help you with that.")
        
        # Return only the requested number
        return suggestions[:num_suggestions]
    
    def query(self, question: str, conversation_context: str = "") -> Dict[str, any]:
        """
        Query the RAG system with a question.
        
        Args:
            question: User's question
            conversation_context: Previous conversation context for continuity
            
        Returns:
            Dictionary with answer and source documents
        """
        if not self.qa_chain:
            raise ValueError("Vector store not initialized. Please process documents first.")
        
        try:
            # Retrieve source documents first
            source_docs = self._retriever.invoke(question)
            
            # Format context
            formatted_context = self._format_docs(source_docs)
            
            # Build prompt with conversation context
            if conversation_context:
                # Include conversation history in the question
                enhanced_question = f"Previous conversation:\n{conversation_context}\n\nCurrent question: {question}"
            else:
                enhanced_question = question
            
            # Create prompt with context awareness
            context_prompt_template = self.prompt_templates.context_prompt_template()
            
            # Format conversation context for prompt
            conv_context_text = f"Previous conversation:\n{conversation_context}\n" if conversation_context else ""
            
            # Build the full prompt
            full_prompt = context_prompt_template.format(
                context=formatted_context,
                conversation_context=conv_context_text,
                question=enhanced_question if conversation_context else question
            )
            
            # Get answer from LLM
            answer = self.llm.invoke(full_prompt)
            
            # Filter source documents - remove technical metadata, keep business-relevant info
            filtered_sources = []
            for doc in source_docs:
                # Extract clean source name (remove file paths, technical details)
                source_name = doc.metadata.get("source", "Document")
                # Clean up source name - remove technical paths
                if "/" in source_name or "\\" in source_name:
                    source_name = source_name.split("/")[-1].split("\\")[-1]
                # Remove file extensions for cleaner display
                if "." in source_name:
                    source_name = source_name.rsplit(".", 1)[0]
                
                # Get clean content (limit length, remove code-like patterns)
                content = doc.page_content[:400] + "..." if len(doc.page_content) > 400 else doc.page_content
                
                # Only include relevant metadata (page number if available)
                clean_metadata = {}
                if "total_pages" in doc.metadata:
                    clean_metadata["pages"] = doc.metadata.get("total_pages", "")
                
                filtered_sources.append({
                    "content": content,
                    "source": source_name,
                    "metadata": clean_metadata
                })
            
            return {
                "answer": answer,
                "source_documents": filtered_sources
            }
        except Exception as e:
            raise Exception(f"Error querying RAG system: {str(e)}")
    
    def load_vectorstore(self):
        """Load existing vector store from disk."""
        loaded = self.vectorstore_manager.load_vectorstore()
        # Sync local handles from manager
        self.vectorstore = self.vectorstore_manager.vectorstore
        self.retriever = self.vectorstore_manager.retriever
        if loaded and self.vectorstore and self.retriever:
            self._create_qa_chain()
            return True
        return False
        
    def get_vectorstore_info(self) -> Dict[str, any]:
        """Get information about the current vector store."""
        return self.vectorstore_manager.get_vectorstore_info()
