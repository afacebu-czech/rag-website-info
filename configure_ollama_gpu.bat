@echo off
echo ========================================
echo Ollama GPU Configuration Helper
echo ========================================
echo.
echo This script helps configure Ollama for maximum GPU usage (~75%).
echo.
echo Note: GPU configuration for Ollama is typically done via:
echo 1. Environment variables
echo 2. Ollama Modelfile (when creating custom models)
echo 3. Ollama server settings
echo.
echo For DeepSeek R1 8B, Ollama automatically uses GPU when available.
echo.
echo To verify GPU usage:
echo 1. Check if Ollama detects your GPU: ollama ps
echo 2. Monitor GPU usage: nvidia-smi (for NVIDIA GPUs)
echo.
echo Current Ollama models:
ollama list
echo.
echo Testing GPU acceleration with a simple query...
ollama run deepseek-r1:8b "Hello" --verbose
echo.
echo ========================================
echo GPU Configuration Tips:
echo ========================================
echo.
echo 1. Ensure your GPU drivers are installed
echo 2. Ollama automatically uses GPU when available
echo 3. Monitor GPU usage with: nvidia-smi -l 1
echo 4. Target GPU utilization: 60-75%%
echo.
echo The RAG system is configured to maximize GPU usage through:
echo - Batch processing for embeddings
echo - Optimized context windows
echo - Parallel document processing
echo.
pause

