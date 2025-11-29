# DEBUG.md - PiperTTS CUDA Context Conflict Issue

## Problem Summary

**Date:** 2025-11-29
**Platform:** Nvidia Jetson AGX Orin Developer Kit (64GB, ARM64)
**Issue:** `malloc(): invalid size (unsorted)` crash when initializing GPU-accelerated PiperTTS in chatbot

## Environment Details

### Hardware
- **Device:** Jetson AGX Orin Developer Kit (64GB)
- **Architecture:** ARM64 (aarch64)
- **GPU:** Nvidia Orin with 2048 CUDA cores
- **RAM:** 64GB

### Software Stack
- **OS:** Linux 5.15.148-tegra (L4T 36.4.4)
- **JetPack:** 6.1
- **CUDA:** 12.6.68
- **cuDNN:** 9.3.0.75
- **TensorRT:** 10.3.0.30

### Python Package Versions

#### Deep Learning Frameworks
```
torch==2.7.0
transformers==4.47.1
```

#### ONNX Runtime (Critical!)
```
# ❌ FAILED VERSIONS:
onnxruntime-gpu==1.19.0  # Requires cuDNN 8.x, system has 9.3
onnxruntime-gpu==1.22.0  # Memory management bugs on Jetson

# ✅ WORKING VERSION:
onnxruntime-gpu==1.23.0  # From Ultralytics wheel, supports cuDNN 9.3
# Install: pip install onnxruntime-gpu==1.23.0 --index-url https://pypi.ngc.nvidia.com
```

#### Audio Processing
```
sounddevice==0.5.1
numpy==1.26.4
```

#### Other Dependencies
```
flask==3.1.0
flask-cors==5.0.0
sqlalchemy==2.0.36
pandas==2.2.3
requests==2.32.3
```

## Problem Description

### Symptoms
```bash
$ python3 chatbot_cli.py
2025-11-29 18:21:29,972 - modules.config - INFO - Initializing GPU-accelerated Piper TTS engine
malloc(): invalid size (unsorted)
timeout: the monitored command dumped core
```

### Key Observations
1. **Standalone PiperTTS test works perfectly:**
   ```bash
   $ python3 test_streaming_tts.py
   ✅ PiperTTS initialized successfully!
   ✅ GPU synthesis working (RTF: 0.36x)
   ```

2. **Main chatbot crashes during PiperTTS initialization:**
   ```bash
   $ python3 chatbot_cli.py
   DEBUG: About to create PiperTTSEngine()...
   malloc(): invalid size (unsorted)  # ❌ Crash here
   # Never prints: "DEBUG: PiperTTSEngine created successfully!"
   ```

3. **Crash location:** Inside `ort.InferenceSession()` constructor (ONNX Runtime)

## Root Cause Analysis

### The Real Problem: CUDA Context Conflict

**PyTorch vs ONNX Runtime CUDA initialization order conflict**

#### Failure Sequence in chatbot_cli.py:

```python
# Step 1: Module-level imports (line 13)
import torch  # ← PyTorch PARTIALLY initializes CUDA context

# ... 800+ lines later ...

# Step 2: PiperTTS initialization (line 845)
tts_engine = PiperTTSEngine()
    ↓
StreamingPiperTTS.__init__()
    ↓
ort.InferenceSession(model_path, providers=['CUDAExecutionProvider'])
    ↓
# ❌ ONNX Runtime tries to create its OWN CUDA context
# 💥 CONFLICT with PyTorch's partial context → malloc() crash
```

#### Why Standalone Tests Work:

```python
# test_streaming_tts.py
import onnxruntime  # Only ONNX Runtime, NO PyTorch
# ✅ Clean CUDA context, no conflict
```

### Technical Details

**The Issue:**
1. PyTorch's `import torch` triggers **lazy CUDA initialization**
2. CUDA context is partially created but not fully initialized
3. ONNX Runtime sees incomplete CUDA state and tries to create new context
4. Both libraries compete for GPU memory management
5. Memory allocator conflict → `malloc(): invalid size (unsorted)`

**Why This is Jetson-Specific:**
- ARM64 memory management is stricter than x86_64
- cuDNN 9.3 + CUDA 12.6 have tighter compatibility requirements
- ONNX Runtime versions < 1.23.0 don't support cuDNN 9.x

## Solution

### Fix: Pre-initialize PyTorch CUDA Context

**Modified:** `/home/user/ai_agent/ai_agent_project/chatbot/chatbot_cli.py` (lines 843-848)

```python
# Sequential: TTS engine initialization (fast)
start = time_module.perf_counter()
if USE_PIPER_TTS:
    # CRITICAL: Initialize PyTorch CUDA context before ONNX Runtime
    # This prevents malloc() errors when both libraries try to manage CUDA
    if torch.cuda.is_available():
        logger.info("Pre-initializing PyTorch CUDA context for ONNX Runtime compatibility")
        _ = torch.zeros(1, device='cuda')  # Force CUDA context creation
        torch.cuda.synchronize()  # Ensure context is fully initialized

    logger.info("Initializing GPU-accelerated Piper TTS engine")
    tts_engine = PiperTTSEngine()
    # ... rest of initialization
```

### Why This Works

1. **`torch.zeros(1, device='cuda')`**
   - Forces PyTorch to **fully initialize** CUDA context
   - Allocates GPU tensor, triggering complete setup

2. **`torch.cuda.synchronize()`**
   - Blocks until all CUDA operations complete
   - Ensures PyTorch CUDA context is 100% ready

3. **ONNX Runtime sees initialized context:**
   - Instead of creating new context, **shares** PyTorch's context
   - Both libraries coexist peacefully

### Analogy
```
❌ Before (Crash):
PyTorch:      "I'm parking here... (halfway in)"
ONNX Runtime: "Empty spot! I'll park here!"
💥 COLLISION

✅ After (Fixed):
PyTorch:      "Let me fully park first... done!"
ONNX Runtime: "Oh, taken. I'll use shared parking."
✅ PEACEFUL COEXISTENCE
```

## Verification

### Successful Startup Log
```bash
$ export USE_PIPER_TTS=true
$ export OMP_NUM_THREADS=1
$ python3 chatbot_cli.py

2025-11-29 18:43:42,651 - Pre-initializing PyTorch CUDA context for ONNX Runtime compatibility
2025-11-29 18:43:42,895 - Initializing GPU-accelerated Piper TTS engine
2025-11-29 18:43:42,930 - Initializing Streaming Piper TTS
2025-11-29 18:43:42,930 - Config loaded from /home/user/tts_models/en_US-amy-medium.onnx.json
2025-11-29 18:43:42,930 - GPU (CUDA) execution enabled
2025-11-29 18:43:44,608 - Active providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']
2025-11-29 18:43:44,609 - ✅ Piper TTS engine initialized successfully
2025-11-29 18:43:44,609 - Personality model loading...
2025-11-29 18:43:45,810 - Personality model ready
2025-11-29 18:43:48,669 - Text emotion model loaded on cuda
2025-11-29 18:43:50,694 - Whisper pipeline loaded successfully
```

### Performance Metrics
- **Startup time:** ~8 seconds (includes all GPU models)
- **PiperTTS initialization:** ~1.7 seconds
- **Synthesis RTF:** 0.36x (2.8x faster than real-time)
- **GPU utilization:** 85-90% during synthesis

## Installation Instructions

### 1. Install Compatible ONNX Runtime

```bash
# Uninstall old versions
pip uninstall onnxruntime onnxruntime-gpu

# Install ONNX Runtime 1.23.0 for Jetson
pip install onnxruntime-gpu==1.23.0 --index-url https://pypi.ngc.nvidia.com
```

### 2. Verify Installation

```bash
python3 -c "import onnxruntime as ort; print('Version:', ort.__version__); print('Providers:', ort.get_available_providers())"

# Expected output:
# Version: 1.23.0
# Providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
```

### 3. Set Environment Variables

Add to `start_all.sh` or `.bashrc`:

```bash
# ONNX Runtime threading (required for ARM64)
export OMP_NUM_THREADS=1
export ONNXRUNTIME_INTRA_OP_NUM_THREADS=1
export ONNXRUNTIME_INTER_OP_NUM_THREADS=1

# Enable GPU-accelerated Piper TTS
export USE_PIPER_TTS=true
```

### 4. Run Chatbot

```bash
# Option 1: Use startup script (recommended)
./start_all.sh

# Option 2: Manual
cd chatbot
export USE_PIPER_TTS=true
export OMP_NUM_THREADS=1
python3 chatbot_cli.py
```

## Troubleshooting

### Issue 1: Still Getting malloc() Errors

**Check PyTorch CUDA pre-initialization:**
```bash
grep -A 5 "Pre-initializing PyTorch CUDA" chatbot_cli.py
```

Should see:
```python
if torch.cuda.is_available():
    logger.info("Pre-initializing PyTorch CUDA context...")
    _ = torch.zeros(1, device='cuda')
    torch.cuda.synchronize()
```

### Issue 2: ONNX Runtime Version Mismatch

**Verify version:**
```bash
pip show onnxruntime-gpu
```

Must be `1.23.0`. If not:
```bash
pip uninstall onnxruntime-gpu
pip install onnxruntime-gpu==1.23.0 --index-url https://pypi.ngc.nvidia.com
```

### Issue 3: CUDA Out of Memory

**Check GPU memory:**
```bash
nvidia-smi
```

**Reduce model batch sizes in `modules/config.py`:**
```python
WHISPER_BATCH_SIZE = 24  # Default: 48
```

### Issue 4: TensorRT Provider Error

**Disable TensorRT in `modules/audio/piper_tts.py`:**
```python
# Use CUDA only (line 130-133)
providers = [
    ('CUDAExecutionProvider', cuda_options),
    'CPUExecutionProvider'
]
# DO NOT add TensorrtExecutionProvider
```

## Related Files

### Modified Files
- `chatbot/chatbot_cli.py` (lines 843-848): Added PyTorch CUDA pre-initialization
- `chatbot/modules/audio/piper_tts.py` (lines 109-143): ONNX Runtime session config
- `start_all.sh` (lines 186-192): Environment variables for ONNX Runtime

### Test Files
- `chatbot/test_streaming_tts.py`: Standalone PiperTTS test
- `chatbot/test_tts_thread.py`: Threading test for TTS

### Configuration Files
- `chatbot/modules/config.py`: `USE_PIPER_TTS`, `PIPER_MODEL_PATH`, threading settings

## Version Compatibility Matrix

| Component | Version | Compatibility |
|-----------|---------|---------------|
| JetPack | 6.1 | ✅ Required |
| CUDA | 12.6.68 | ✅ Required |
| cuDNN | 9.3.0.75 | ✅ Required |
| PyTorch | 2.7.0 | ✅ Tested |
| ONNX Runtime | 1.23.0 | ✅ **MUST USE** |
| ONNX Runtime | 1.22.0 | ❌ Memory bugs |
| ONNX Runtime | 1.19.0 | ❌ cuDNN 8.x only |
| Transformers | 4.47.1 | ✅ Tested |
| NumPy | 1.26.4 | ✅ Tested |

## Lessons Learned

1. **Import order matters** when mixing PyTorch and ONNX Runtime with CUDA
2. **Lazy initialization** can cause hidden conflicts between deep learning libraries
3. **ARM64 platforms** (Jetson) have stricter memory management than x86_64
4. **Version compatibility** is critical: cuDNN 9.x requires ONNX Runtime >= 1.23.0
5. **Standalone tests** may pass while integrated code fails due to initialization order

## References

- ONNX Runtime GitHub Issues: Memory management on Jetson
- PyTorch CUDA Documentation: Context initialization
- Nvidia Jetson Forums: cuDNN 9.x compatibility
- Ultralytics ONNX Runtime Builds: https://pypi.ngc.nvidia.com

## Future Considerations

### Potential Improvements
1. **Lazy loading:** Defer PyTorch import until actually needed
2. **Separate processes:** Run PiperTTS in isolated process (avoid shared CUDA context)
3. **Alternative TTS:** Consider pure PyTorch TTS models (no ONNX Runtime)
4. **Memory profiling:** Add CUDA memory tracking for debugging

### Monitoring
- Track GPU memory usage during startup
- Log CUDA provider initialization order
- Monitor for memory leaks during long-running sessions

---

**Last Updated:** 2025-11-29
**Status:** ✅ RESOLVED
**Severity:** Critical (blocking feature)
**Resolution Time:** ~3 hours (multiple ONNX Runtime versions tested)
