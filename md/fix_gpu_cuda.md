# GPU/CUDA Detection Fix Guide

## Problem
Your system shows "GPU not available (CUDA not detected)" even though CPU-Z shows your NVIDIA GeForce GTX 1050 Ti is detected.

## Root Cause
This is a **PyTorch CUDA configuration issue**, not a hardware problem. PyTorch was likely installed without CUDA support (CPU-only version).

## Solution

### Step 1: Check Current PyTorch Installation
```bash
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available())"
```

### Step 2: Install PyTorch with CUDA Support

For **CUDA 11.8** (recommended for GTX 1050 Ti):
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

For **CUDA 12.1**:
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 3: Verify CUDA Installation
```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'N/A'); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

### Step 4: Install CUDA Toolkit (if needed)
If Step 2 doesn't work, you may need to install the CUDA Toolkit:
1. Download from: https://developer.nvidia.com/cuda-downloads
2. Install CUDA Toolkit 11.8 or 12.1
3. Restart your computer
4. Re-run Step 2

### Step 5: Restart the Application
After installing PyTorch with CUDA, restart your Streamlit app. You should see:
```
✅ EasyOCR initialized with GPU: NVIDIA GeForce GTX 1050 Ti
```

## Alternative: Check CUDA Installation
```bash
nvidia-smi
```
This should show your GPU. If it doesn't, update your NVIDIA drivers first.

## Troubleshooting

### Issue: "CUDA version mismatch"
- Uninstall PyTorch: `pip uninstall torch torchvision torchaudio`
- Install matching CUDA version: Check `nvidia-smi` for your CUDA version
- Install matching PyTorch: Use the appropriate `--index-url` for your CUDA version

### Issue: "CUDA out of memory"
- Your GTX 1050 Ti has 4GB VRAM - this should be enough for EasyOCR
- If you still get errors, the system will automatically fall back to CPU

### Issue: "No module named torch"
- Install PyTorch: `pip install torch`

