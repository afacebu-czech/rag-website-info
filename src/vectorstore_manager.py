from typing import Dict, List
from langchain_core.documents import Document
import src.config as config
import os
from langchain_ollama import OllamaEmbeddings
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to community version
    from langchain_community.vectorstores import Chroma

class VectorstoreManager:
    def __init__(self, embeddings: OllamaEmbeddings):
        self.embeddings = embeddings
        self.vectorstore = None
        self.retriever = None
        
    def create_vectorstore(self, documents: List[Document], persist: bool = True):
        """Create or update vectorstore from documents with batch processing for GPU optimization"""
        if not documents:
            raise ValueError("No documents provided")
        
        try:
            batch_size = getattr(config, 'EMBEDDING_BATCH_SIZE', 200)
            
            if persist and os.path.exists(config.PERSIST_DIRECTORY):
                self.vectorstore = Chroma(
                    persist_directory=config.PERSIST_DIRECTORY,
                    embedding_function=self.embeddings,
                )
                if len(documents) > batch_size:
                    for i in range(0, len(documents), batch_size):
                        batch = documents[i:i + batch_size]
                        self.vectorstore.add_documents(batch)
                        print(f"Processed batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size} ({len(batch)} chunks)")
                else:
                    self.vectorstore.add_documents(documents)
            else:
                # Create new vector store with batch processing
                self.vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                    persist_directory=config.PERSIST_DIRECTORY if persist else None
                )
            
            # Create retriever
            self.retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": config.TOP_K}
            )
            
            print(f"Vector store created with {len(documents)} document chunks (GPU optimized)")
            
        except Exception as e:
            raise Exception(f"Failed to create vector store: {str(e)}")
        
    def load_vectorstore(self):
        """Load existing vectorstore from disk"""
        try:
            if os.path.exists(config.PERSIST_DIRECTORY):
                self.vectorstore = Chroma(
                    persist_directory=config.PERSIST_DIRECTORY,
                    embedding_function=self.embeddings
                )
                self.retriever = self.vectorstore.as_retriever(
                    search_kwargs={"k": config.TOP_K}
                )
                
                print("Vector store loaded from disk")
                return True
            else:
                print("No existing vector stores found")
                return False
        except Exception as e:
            print(f"Error loading vector store: {str(e)}")
            return False
        
    def get_vectorstore_info(self) -> Dict[str, any]:
        """Get information about the current vector store."""
        if not self.vectorstore:
            return {"status": "not_initialized"}
        
        try:
            # Get collection count
            collection = getattr(self.vectorstore, "_collection", None)
            count = collection.count() if collection else 0
            
            persist_path = getattr(config, "PERSIST_DIRECTORY", None)
            sqlite_path = os.path.join(persist_path, "chroma.sqlite3") if persist_path else None
            sqlite_exists = os.path.exists(sqlite_path) if sqlite_path else False
            
            return {
                "status": "initialized",
                "document_count": count,
                "persist_directory": persist_path if sqlite_exists else None
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }