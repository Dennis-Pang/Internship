# PDF to Markdown Converter

GPU-accelerated PDF conversion using MinerU, optimized for ARM64 (Nvidia Jetson Orin).

## Features

- GPU acceleration (PyTorch 2.7.0 + CUDA 12.6)
- 10-15x faster than CPU
- Multi-language OCR support
- ARM64 optimized

## Usage

```bash
cd agentic-report-gen
python tools/pdf_to_markdown.py document.pdf       # GPU (default)
python tools/pdf_to_markdown.py document.pdf --device cpu  # CPU mode
python tools/pdf_to_markdown.py document.pdf --lang ch     # Chinese PDF
```

## Performance

| Mode | Speed |
|------|-------|
| GPU | ~1.3s/page |
| CPU | ~19s/page |

## Output

`data/markdown/document_name/auto/document_name.md`
