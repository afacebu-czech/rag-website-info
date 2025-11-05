# Quick Start Guide

## ✅ Pre-requisites Check

Before running the application, verify:

1. **Ollama is installed and running:**
   ```bash
   ollama --version
   ollama list
   ```
   You should see `deepseek-r1:8b` in the list.

2. **Python packages are installed:**
   ```bash
   pip list | findstr "langchain streamlit pdfplumber"
   ```

## 🚀 Running the Application

### Step 1: Start Ollama (if not running as a service)

```bash
ollama serve
```

Keep this terminal open. In a new terminal, proceed to Step 2.

### Step 2: Run the Streamlit App

**For local access only:**
```bash
streamlit run app.py
```

**For network access (from other PCs):**
```bash
# Option 1: Use the batch file
run_app_network.bat

# Option 2: Use command line
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

The application will automatically open in your browser at `http://localhost:8501`

**To access from another PC on your network:**
1. Find your PC's IP address: `ipconfig` (look for "IPv4 Address")
2. On the other PC, open: `http://YOUR_IP_ADDRESS:8501`
3. Example: `http://192.168.1.100:8501`

📖 See `NETWORK_ACCESS_GUIDE.md` for detailed network access instructions and troubleshooting.

## 📝 First Time Usage

1. **Upload Documents:**
   - Click on "Upload Documents" tab
   - Select one or more PDF files
   - Click "Process Documents"
   - Wait for processing to complete (may take a minute for large PDFs)

2. **Start Chatting:**
   - Click on "Chat with Documents" tab
   - Type your question
   - Get answers with source citations!

## 🔍 Testing the System

### Test 1: Verify Ollama Connection

```bash
ollama run deepseek-r1:8b "Hello, how are you?"
```

### Test 2: Test PDF Processing

Place a test PDF in `data/uploads/` and upload it through the UI.

### Test 3: Test Query

After processing documents, ask:
- "What is this document about?"
- "Summarize the main points"
- "What are the key concepts?"

## ⚠️ Common Issues

### Issue: "Failed to initialize LLM"

**Solution:**
- Check Ollama is running: `ollama serve`
- Verify model: `ollama list`
- Check firewall isn't blocking port 11434

### Issue: "No documents loaded"

**Solution:**
- Make sure you've uploaded and processed documents
- Check the "Upload Documents" tab shows success
- Verify PDFs are not corrupted

### Issue: Slow response times

**Solution:**
- Reduce `TOP_K` in `config.py` (default: 4)
- Process smaller documents
- Close other applications to free up RAM

## 📊 System Requirements

- **RAM:** Minimum 16GB (8GB for model + 8GB for system)
- **Storage:** ~10GB free space
- **CPU:** Multi-core recommended (4+ cores)
- **GPU:** Optional but recommended for faster inference

## 🎯 Next Steps

After successful setup:

1. **Customize Configuration:**
   - Edit `config.py` to adjust chunk size, temperature, etc.
   - Create `.env` file for environment-specific settings

2. **Process Your Documents:**
   - Upload PDFs relevant to your use case
   - Test with various document types

3. **Optimize Performance:**
   - Adjust `CHUNK_SIZE` for your document types
   - Tune `TOP_K` for retrieval quality
   - Experiment with `TEMPERATURE` for response style

