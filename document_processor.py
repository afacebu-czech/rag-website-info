"""
Document processing module for extracting and chunking PDF documents.
"""
import os
import pdfplumber
from typing import List, Dict, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import config
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing


class DocumentProcessor:
    """Process PDF documents and create chunks for RAG."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of text chunks (default from config)
            chunk_overlap: Overlap between chunks (default from config)
        """
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
    
    def extract_text_from_pdf(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary with text content and metadata
        """
        try:
            text_content = []
            metadata = {
                "source": os.path.basename(file_path),
                "file_path": file_path,
                "total_pages": 0,
            }
            
            with pdfplumber.open(file_path) as pdf:
                metadata["total_pages"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        text_content.append({
                            "page": page_num,
                            "text": text.strip()
                        })
            
            full_text = "\n\n".join([item["text"] for item in text_content])
            
            return {
                "text": full_text,
                "metadata": metadata,
                "page_data": text_content
            }
            
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def create_chunks(self, text: str, metadata: Dict = None) -> List[Document]:
        """
        Create document chunks from text.
        
        Args:
            text: Full text content
            metadata: Document metadata
            
        Returns:
            List of Document objects with chunks
        """
        try:
            # Use recursive text splitter for chunking
            text_chunks = self.text_splitter.split_text(text)
            documents = []
            
            for i, chunk in enumerate(text_chunks):
                chunk_metadata = {
                    **(metadata or {}),
                    "chunk_id": i,
                    "chunk_size": len(chunk)
                }
                documents.append(Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                ))
            
            return documents
            
        except Exception as e:
            raise Exception(f"Error creating chunks: {str(e)}")
    
    def process_pdf(self, file_path: str) -> List[Document]:
        """
        Complete PDF processing pipeline: extract and chunk.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of Document chunks
        """
        # Extract text
        extraction_result = self.extract_text_from_pdf(file_path)
        
        # Create chunks
        documents = self.create_chunks(
            extraction_result["text"],
            extraction_result["metadata"]
        )
        
        return documents
    
    def process_multiple_pdfs(self, file_paths: List[str]) -> List[Document]:
        """
        Process multiple PDF files with parallel processing for faster execution.
        
        Args:
            file_paths: List of PDF file paths
            
        Returns:
            Combined list of all document chunks
        """
        all_documents = []
        
        # Use parallel processing if enabled and multiple files
        if config.PARALLEL_PROCESSING and len(file_paths) > 1:
            # Determine number of workers
            max_workers = config.MAX_WORKERS if config.MAX_WORKERS > 0 else min(len(file_paths), multiprocessing.cpu_count())
            
            print(f"Processing {len(file_paths)} PDF files in parallel using {max_workers} workers...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.process_pdf, file_path): file_path 
                    for file_path in file_paths
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        documents = future.result()
                        all_documents.extend(documents)
                        print(f"✓ Processed: {os.path.basename(file_path)} ({len(documents)} chunks)")
                    except Exception as e:
                        print(f"✗ Error processing {file_path}: {str(e)}")
                        continue
        else:
            # Sequential processing (fallback or single file)
            for file_path in file_paths:
                try:
                    documents = self.process_pdf(file_path)
                    all_documents.extend(documents)
                    print(f"✓ Processed: {os.path.basename(file_path)} ({len(documents)} chunks)")
                except Exception as e:
                    print(f"✗ Error processing {file_path}: {str(e)}")
                    continue
        
        return all_documents

