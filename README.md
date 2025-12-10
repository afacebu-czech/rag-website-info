# Local RAG System - Llama-3-8B

A powerful Retrieval-Augmented Generation (RAG) system running locally on Windows using Ollama, DeepSeek R1 8B, and Python.

## 🎯 Overview

This system allows you to:

- Upload PDF documents
- Process and chunk documents using semantic chunking
- Create a vector database for fast retrieval
- Query documents using DeepSeek R1 8B model locally
- Get answers with source citations

## 📋 Prerequisites

- **Windows 10/11**
- **Python 3.13+**
- **Ollama** installed and running
- **Llama-3-8B** model downloaded
- **Minimum 16GB RAM** (8GB for model + 8GB for system)

## 🚀 Quick Start

### 1. Install Ollama

Download and install Ollama from [ollama.ai](https://ollama.ai)

### 2. Download DeepSeek R1 8B Model

```bash
ollama pull Llama-3-8B
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Ollama is Running

```bash
ollama list
```

You should see `deepseek-r1:8b` in the list.

### 5. Run the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
CursorProj/
├── Chat.py                 # Main Streamlit application
├── src
│    └── utils
│         ├── __init__.py
│
├── rag_system.py           # RAG core logic
├── document_processor.py   # PDF processing
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── data/                   # Uploaded documents
│   └── uploads/
├── vectorstore/            # Vector database storage
│   └── chroma_db/
└── README.md
```

## 🔧 Configuration

Edit `config.py` or create a `.env` file to customize:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b
EMBEDDING_MODEL=deepseek-r1:8b
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K=4
TEMPERATURE=0.7
```

## 📖 Usage

### Step 1: Upload Documents

1. Go to the "Upload Documents" tab
2. Select one or more PDF files
3. Click "Process Documents"
4. Wait for processing to complete

### Step 2: Chat with Documents

1. Go to the "Chat with Documents" tab
2. Type your question in the chat input
3. Get answers with source citations

## 🛠️ Troubleshooting

### Ollama Connection Error

**Problem:** "Failed to initialize LLM"

**Solution:**

- Make sure Ollama is running: `ollama serve`
- Verify the model is downloaded: `ollama list`
- Check the API endpoint in `config.py`

### Memory Issues

**Problem:** System runs out of memory

**Solution:**

- Reduce `CHUNK_SIZE` in `config.py`
- Process fewer documents at once
- Close other applications

### PDF Processing Errors

**Problem:** "Error extracting text from PDF"

**Solution:**

- Verify PDF is not corrupted
- Check file size limits
- Ensure PDF is not password-protected

## 📚 Technical Details

### Architecture

- **Document Processing:** PDF text extraction using `pdfplumber`
- **Chunking:** Semantic chunking for better context preservation
- **Vector Store:** ChromaDB for fast similarity search
- **Embeddings:** Ollama embeddings (DeepSeek R1 8B)
- **LLM:** DeepSeek R1 8B via Ollama
- **Framework:** LangChain for RAG pipeline

### RAG Pipeline

1. **Document Upload** → PDF files uploaded
2. **Text Extraction** → Text extracted from PDFs
3. **Chunking** → Documents split into semantic chunks
4. **Embedding** → Chunks converted to vectors
5. **Vector Store** → Vectors stored in ChromaDB
6. **Query** → User question processed
7. **Retrieval** → Relevant chunks retrieved
8. **Generation** → LLM generates answer with context
9. **Response** → Answer with source citations

## 🔗 References

- [Ollama Documentation](https://ollama.ai/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [DeepSeek R1 Model](https://huggingface.co/deepseek-ai/DeepSeek-R1)
- [Original Article](https://dev.to/ajmal_hasan/setting-up-ollama-running-deepseek-r1-locally-for-a-powerful-rag-system-4pd4)

## 📝 License

This project is open source and available for educational purposes.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
