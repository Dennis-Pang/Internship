# ONNX Runtime Bug on Jetson AGX Orin

## Environment

- **Device**: Nvidia Jetson AGX Orin 64GB
- **JetPack**: 6.1
- **CUDA**: 12.6
- **cuDNN**: 9.3
- **Python**: 3.10
- **Torch**: 2.7.0 (aarch64, CUDA)
- **ONNX Runtime GPU**: 1.22.0 (custom wheel for aarch64)

## Symptoms

### Error 1: `free(): invalid pointer`

```
import onnxruntime as ort
print(ort.get_available_providers())
# Output: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
# Then on exit:
free(): invalid pointer
Aborted (core dumped)
```

**Trigger**: Python interpreter exit/cleanup after importing onnxruntime
**Impact**: Crash on exit, but functionality works during execution

### Error 2: `malloc(): invalid size (unsorted)`

```
import onnxruntime as ort
import torch
from neutts import NeuTTS
# Crash during initialization:
malloc(): invalid size (unsorted)
Aborted (core dumped)
```

**Trigger**: Combining onnxruntime with torch when both try to use CUDA
**Impact**: Crash during execution, blocks functionality

## Root Cause Analysis

1. **Library Cleanup Conflict**: ONNX Runtime and PyTorch both register cleanup handlers for CUDA resources. When Python exits, the cleanup order causes `free()` to be called on already-freed memory.

2. **CUDA Context Conflict**: Both libraries initialize CUDA contexts. When ONNX Runtime's CUDA/TensorRT execution providers load, they conflict with PyTorch's CUDA context, causing memory corruption (`malloc(): invalid size`).

3. **ARM64/Tegra Specific**: The `cpuinfo` library used by ONNX Runtime doesn't properly detect Tegra ARM processors:
   ```
   onnxruntime cpuid_info warning: Unknown CPU vendor. cpuinfo_vendor value: 0
   ```

## Solution

### Workaround 1: Hide CUDA from ONNX Runtime

Set `CUDA_VISIBLE_DEVICES=""` before importing onnxruntime to prevent it from initializing CUDA providers:

```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Must be set BEFORE import

import onnxruntime as ort
# Now only CPUExecutionProvider will be used effectively
```

### Workaround 2: Use `os._exit(0)` to Skip Cleanup

If exit crash is acceptable (doesn't affect functionality):

```python
import os
# ... your code ...
os._exit(0)  # Skip Python cleanup, avoid free() crash
```

### Workaround 3: Run from Script File

Running from a `.py` file instead of heredoc/interactive mode reduces crash frequency:

```bash
# Instead of:
python3 -c "import onnxruntime; ..."

# Use:
python3 /path/to/script.py
```

## Recommended Configuration for NeuTTS

For running NeuTTS with GGUF backbone + ONNX codec on Jetson:

```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Hide CUDA from ORT

import onnxruntime as ort
import torch  # torch still uses GPU normally

from neutts import NeuTTS

tts = NeuTTS(
    backbone_repo='neuphonic/neutts-nano-q4-gguf',
    backbone_device='cpu',      # GGUF runs on CPU (llama-cpp)
    codec_repo='neuphonic/neucodec-onnx-decoder',
    codec_device='cpu',         # ONNX decoder on CPU
)

# At script end, use os._exit(0) to avoid cleanup crash
os._exit(0)
```

### Performance with This Configuration

| Metric | GGUF + ONNX (CPU) | GGUF + PyTorch (CPU) | PyTorch (GPU) |
|--------|-------------------|----------------------|---------------|
| Init Time | **5.9s** | 16s | 133s |
| RTF | **~2.3x** | ~2.9x | ~5x |
| GPU Usage | None (free for LLM) | None | Conflicts with LLM |

## Architecture for Chatbot

```
┌─────────────────────────────────────────────────────────────┐
│                      Ollama (GPU)                           │
│                   LLM Text Generation                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ Streaming text
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    NeuTTS (CPU)                             │
│    GGUF backbone (llama-cpp) + ONNX codec decoder          │
│    CUDA_VISIBLE_DEVICES="" to isolate from GPU             │
└─────────────────────────────────────────────────────────────┘
```

This allows LLM and TTS to run in parallel without GPU conflicts.

## Related Issues

- [Jetson Containers #1403](https://github.com/dusty-nv/jetson-containers/issues/1403) - Piper TTS fails on Jetson AGX Orin
- [ONNX Runtime #10038](https://github.com/microsoft/onnxruntime/issues/10038) - ARM64 Lambda crash
- [NVIDIA Forums](https://forums.developer.nvidia.com/t/free-invalid-pointer-aborted-dump-error/331283) - free(): invalid pointer on Jetson Orin NX

## Final Solution Used

Due to the complexity of isolating CUDA_VISIBLE_DEVICES without breaking other GPU-dependent modules (Whisper, emotion models), we use **GGUF backbone + PyTorch codec** instead of ONNX:

```python
# config.py
NEUTTS_BACKBONE_REPO = "neuphonic/neutts-nano-q4-gguf"  # GGUF on CPU
NEUTTS_CODEC_REPO = "neuphonic/neucodec"                # PyTorch on CPU (not ONNX)
NEUTTS_DEVICE = "cpu"
```

### Performance Comparison

| Configuration | Init Time | RTF | GPU Usage |
|--------------|-----------|-----|-----------|
| PyTorch backbone (GPU) | 133s | ~5x | Conflicts with Ollama |
| GGUF + ONNX (CPU) | 6s | ~2.3x | None (requires CUDA isolation) |
| **GGUF + PyTorch (CPU)** | **12s** | **~4x** | **None (no isolation needed)** |

The GGUF + PyTorch solution is chosen because:
1. No CUDA isolation needed - works with existing GPU modules
2. Reasonable performance (RTF ~4x)
3. Stable and reliable on Jetson ARM64

## Date

2026-01-21
