#!/usr/bin/env python
"""
PDF to Markdown Parser using MinerU
Optimized for ARM64 (Nvidia Jetson Orin) with CUDA support

Usage:
    python pdf_to_markdown.py <pdf_path>
    python pdf_to_markdown.py <pdf_path> --output /custom/path
    python pdf_to_markdown.py <pdf_path> --lang ch --device cuda
"""
import os
import sys
import argparse
import glob
from pathlib import Path
from loguru import logger

# Set environment variables for ARM64 compatibility (must be set before importing MinerU)
# These prevent ONNX Runtime threading issues on ARM64
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MINERU_INTRA_OP_NUM_THREADS', '1')
os.environ.setdefault('MINERU_INTER_OP_NUM_THREADS', '1')

# Import MinerU components
from mineru.cli.common import do_parse, read_fn
from mineru.utils.config_reader import get_device
from mineru.utils.model_utils import get_vram


def parse_pdf(
    pdf_path: str,
    output_dir: str = None,
    backend: str = "pipeline",
    method: str = "auto",
    lang: str = "en",
    formula_enable: bool = False,  # Default False for ARM64 stability
    table_enable: bool = False,    # Default False for ARM64 stability
    device_mode: str = None,
):
    """
    Parse a PDF file using MinerU and save results as Markdown.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Output directory for markdown results
        backend: Backend to use ('pipeline', 'vlm-transformers', 'vlm-vllm-engine', 'vlm-http-client')
        method: Parsing method ('auto', 'txt', 'ocr')
        lang: Language for OCR ('en', 'ch', etc.)
        formula_enable: Enable formula parsing (may cause crashes on ARM64)
        table_enable: Enable table parsing (may cause crashes on ARM64)
        device_mode: Device mode ('cpu', 'cuda', 'cuda:0', etc.)
    """
    # Set default output directory
    if output_dir is None:
        output_dir = "/home/user/ai_agent/ai_agent_project/agentic-report-gen/data/markdown"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Validate PDF path
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    logger.info(f"Parsing PDF: {pdf_path}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Backend: {backend}")

    # Set environment variables for device mode
    if device_mode is None:
        device_mode = get_device()

    # Check if CUDA is actually available when requested
    if device_mode.startswith("cuda"):
        try:
            import torch
            if not torch.cuda.is_available():
                logger.warning("⚠️  CUDA requested but not available in PyTorch!")
                logger.warning("⚠️  Falling back to CPU mode.")
                logger.info("To enable CUDA on Jetson Orin, install PyTorch with CUDA support:")
                logger.info("  pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu126")
                device_mode = "cpu"
        except ImportError:
            logger.warning("PyTorch not found, using CPU mode")
            device_mode = "cpu"

    os.environ['MINERU_DEVICE_MODE'] = device_mode
    logger.info(f"Device mode: {device_mode}")

    # Set virtual VRAM size
    if device_mode.startswith("cuda") or device_mode.startswith("npu"):
        try:
            vram_size = round(get_vram(device_mode))
            logger.info(f"Detected VRAM: {vram_size}GB")
        except Exception as e:
            logger.warning(f"Could not detect VRAM: {e}. Using default value.")
            vram_size = 8  # Default for Jetson Orin
    else:
        vram_size = 1
    os.environ['MINERU_VIRTUAL_VRAM_SIZE'] = str(vram_size)

    # Set model source (using huggingface by default)
    os.environ['MINERU_MODEL_SOURCE'] = 'huggingface'

    try:
        # Read PDF file
        file_name = str(pdf_path.stem)
        pdf_bytes = read_fn(pdf_path)

        # Parse the PDF
        logger.info("Starting PDF parsing...")
        if formula_enable or table_enable:
            logger.warning("Formula and/or table parsing enabled. This may cause crashes on ARM64.")

        do_parse(
            output_dir=output_dir,
            pdf_file_names=[file_name],
            pdf_bytes_list=[pdf_bytes],
            p_lang_list=[lang],
            backend=backend,
            parse_method=method,
            formula_enable=formula_enable,
            table_enable=table_enable,
            server_url=None,
            start_page_id=0,
            end_page_id=None,
        )

        logger.success(f"PDF parsing completed! Results saved to: {output_dir}")

        # Find and display the markdown output (may be in auto subdirectory)
        possible_paths = [
            Path(output_dir) / file_name / method / f"{file_name}.md",  # with method subdir
            Path(output_dir) / file_name / f"{file_name}.md",  # direct
        ]

        markdown_file = None
        for path in possible_paths:
            if path.exists():
                markdown_file = path
                break

        if markdown_file:
            logger.success(f"Markdown file created: {markdown_file}")
            return str(markdown_file)
        else:
            # Try to find any .md file in the output directory
            md_files = glob.glob(f"{output_dir}/{file_name}/**/*.md", recursive=True)
            if md_files:
                markdown_file = md_files[0]
                logger.success(f"Markdown file found: {markdown_file}")
                return str(markdown_file)
            else:
                logger.warning(f"Markdown file not found in: {output_dir}/{file_name}/")
                logger.info(f"Check output directory for results: {output_dir}/{file_name}/")
                return None

    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Parse PDF files using MinerU and save as Markdown (ARM64/CUDA optimized)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Parse with default settings (CPU mode, no formula/table)
    python pdf_to_markdown.py document.pdf

    # Parse with GPU acceleration
    python pdf_to_markdown.py document.pdf --device cuda

    # Parse Chinese PDF with GPU
    python pdf_to_markdown.py document.pdf --lang ch --device cuda

    # Enable formula and table parsing (may be unstable on ARM64)
    python pdf_to_markdown.py document.pdf --enable-formula --enable-table

    # Specify custom output directory
    python pdf_to_markdown.py document.pdf --output /path/to/output

Note: For maximum stability on ARM64, avoid enabling formula and table parsing.
      GPU mode (--device cuda) can significantly speed up processing.
        """
    )

    parser.add_argument(
        "pdf_path",
        help="Path to the PDF file to parse"
    )

    parser.add_argument(
        "-o", "--output",
        default="/home/user/ai_agent/ai_agent_project/agentic-report-gen/data/markdown",
        help="Output directory for markdown results (default: ./data/markdown)"
    )

    parser.add_argument(
        "-b", "--backend",
        default="pipeline",
        choices=["pipeline", "vlm-transformers", "vlm-vllm-engine", "vlm-http-client"],
        help="Backend to use for parsing (default: pipeline)"
    )

    parser.add_argument(
        "-m", "--method",
        default="auto",
        choices=["auto", "txt", "ocr"],
        help="Parsing method (default: auto)"
    )

    parser.add_argument(
        "-l", "--lang",
        default="en",
        choices=['ch', 'ch_server', 'ch_lite', 'en', 'korean', 'japan',
                 'chinese_cht', 'ta', 'te', 'ka', 'th', 'el', 'latin',
                 'arabic', 'east_slavic', 'cyrillic', 'devanagari'],
        help="Language for OCR (default: en)"
    )

    parser.add_argument(
        "--enable-formula",
        action="store_true",
        help="Enable formula parsing (WARNING: may cause crashes on ARM64)"
    )

    parser.add_argument(
        "--enable-table",
        action="store_true",
        help="Enable table parsing (WARNING: may cause crashes on ARM64)"
    )

    parser.add_argument(
        "-d", "--device",
        default="cuda",
        choices=["cpu", "cuda", "cuda:0"],
        help="Device mode (cpu, cuda, cuda:0). Default: cuda (GPU). Use 'cpu' to disable GPU acceleration."
    )

    args = parser.parse_args()

    # Show warning if formula/table parsing is enabled
    if args.enable_formula or args.enable_table:
        logger.warning("⚠️  Formula and/or table parsing enabled!")
        logger.warning("⚠️  This may cause crashes on ARM64 architecture.")
        logger.warning("⚠️  If you encounter issues, run without --enable-formula and --enable-table")

    try:
        result = parse_pdf(
            pdf_path=args.pdf_path,
            output_dir=args.output,
            backend=args.backend,
            method=args.method,
            lang=args.lang,
            formula_enable=args.enable_formula,
            table_enable=args.enable_table,
            device_mode=args.device,
        )

        if result:
            print(f"\n✅ Success! Markdown saved to: {result}")
        else:
            print(f"\n✅ Parsing completed! Check output directory: {args.output}")

        return 0

    except Exception as e:
        logger.error(f"Failed to parse PDF: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
