#!/usr/bin/env python
"""
Main entry point for the Multi-Agent Medical Report Generation System

Usage:
    python main.py --request "Generate report for patient" --pdf file1.pdf file2.pdf
    python main.py --request "Analyze lab results" --tabular labs.csv --pdf discharge.pdf
    python main.py --help
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

# Import agent system
from agent import Config, generate_medical_report


def setup_logging(verbose: bool = False):
    """Configure logging"""
    logger.remove()  # Remove default handler

    log_level = "DEBUG" if verbose else "INFO"

    # Console output
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )

    # File output
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "agent_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    )


async def main_async(args):
    """Main async function"""

    # Load config
    config = Config()

    # Collect files
    pdf_files = args.pdf or []
    tabular_files = args.tabular or []
    sensor_files = args.sensor or []

    # Validate files exist
    all_files = pdf_files + tabular_files + sensor_files
    for file_path in all_files:
        if not Path(file_path).exists():
            logger.error(f"File not found: {file_path}")
            return 1

    # Display configuration
    logger.info("=" * 80)
    logger.info("Multi-Agent Medical Report Generation System")
    logger.info("=" * 80)
    logger.info(f"User Request: {args.request}")
    logger.info(f"PDF Files: {len(pdf_files)}")
    logger.info(f"Tabular Files: {len(tabular_files)}")
    logger.info(f"Sensor Files: {len(sensor_files)}")
    logger.info(f"Model: {config.DEEPSEEK_MODEL}")
    logger.info(f"API Base: {config.DEEPSEEK_API_BASE}")
    logger.info(f"Langfuse: {'Enabled' if config.LANGFUSE_ENABLED else 'Disabled'}")
    logger.info("=" * 80)

    try:
        # Generate report
        result = await generate_medical_report(
            user_request=args.request,
            pdf_files=pdf_files,
            tabular_files=tabular_files,
            sensor_files=sensor_files,
            config=config
        )

        # Save output
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"report_{timestamp}.json"
        report_file = output_dir / f"report_{timestamp}.md"

        # Save complete result as JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.success(f"Full result saved to: {output_file}")

        # Save final report as markdown
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(result['final_report'])

        logger.success(f"Final report saved to: {report_file}")

        # Print report to console if requested
        if args.print_report:
            print("\n" + "=" * 80)
            print("FINAL REPORT")
            print("=" * 80)
            print(result['final_report'])
            print("=" * 80)

        logger.info(f"\nExecution time: {result['execution_time_seconds']:.2f} seconds")

        return 0

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Medical Report Generation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Generate report from PDF files
    python main.py --request "Generate comprehensive patient report" --pdf discharge.pdf labs.pdf

    # Process multiple data types
    python main.py --request "Analyze patient data" --pdf report.pdf --tabular labs.csv

    # Chinese PDF
    python main.py --request "生成患者报告" --pdf chinese_report.pdf

    # Print report to console
    python main.py --request "Quick summary" --pdf summary.pdf --print

Environment Variables:
    DEEPSEEK_API_BASE    - DeepSeek API endpoint (default: http://localhost:8000/v1)
    DEEPSEEK_API_KEY     - API key for authentication
    DEEPSEEK_MODEL       - Model name (default: deepseek-reasoner)
    LANGFUSE_ENABLED     - Enable observability (default: false)

See .env.example for all configuration options.
        """
    )

    parser.add_argument(
        "-r", "--request",
        required=True,
        help="Natural language description of the desired report"
    )

    parser.add_argument(
        "--pdf",
        nargs="+",
        help="PDF files to process"
    )

    parser.add_argument(
        "--tabular",
        nargs="+",
        help="Tabular files to process (CSV, XLSX) - placeholder"
    )

    parser.add_argument(
        "--sensor",
        nargs="+",
        help="Sensor/time-series data files - placeholder"
    )

    parser.add_argument(
        "-o", "--output-dir",
        default="./output",
        help="Output directory for generated reports (default: ./output)"
    )

    parser.add_argument(
        "-p", "--print-report",
        action="store_true",
        help="Print final report to console"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    # Check if any files provided
    if not args.pdf and not args.tabular and not args.sensor:
        logger.error("No input files provided. Use --pdf, --tabular, or --sensor")
        parser.print_help()
        return 1

    # Run async main
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
