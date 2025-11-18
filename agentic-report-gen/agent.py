"""
Multi-Agent Medical Report Generation System

A multi-agent system for generating medical reports from various data sources:
- Tabular data (CSV, XLSX) - placeholder
- Sensor data (time-series) - placeholder
- PDF/Text documents (processed via pdf_to_markdown.py)

Uses DeepSeek R1 model with Langfuse observability.
"""

import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

try:
    from openai import AsyncOpenAI
except ImportError:
    logger.warning("openai package not installed. Please run: pip install openai")
    AsyncOpenAI = None

try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
except ImportError:
    logger.warning("langfuse package not installed. Observability will be disabled.")
    logger.warning("To enable: pip install langfuse")
    Langfuse = None
    observe = lambda func: func  # No-op decorator
    langfuse_context = None


class Config:
    """Configuration for the multi-agent system"""

    def __init__(self):
        # Paths
        self.BASE_DIR = Path(__file__).parent
        self.PROMPTS_DIR = self.BASE_DIR / "prompts"
        self.DATA_DIR = self.BASE_DIR / "data"
        self.PDF_DIR = self.DATA_DIR / "pdf"
        self.MARKDOWN_DIR = self.DATA_DIR / "markdown"
        self.PDF_TO_MARKDOWN_SCRIPT = self.BASE_DIR / "tools" / "pdf_to_markdown.py"

        # DeepSeek API
        self.DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "http://localhost:8000/v1")
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key")
        self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

        # Langfuse
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
        self.LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
        self.LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

        # Model parameters
        self.TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
        self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
        self.AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))

        # PDF processing
        self.PDF_DEFAULT_LANG = os.getenv("PDF_DEFAULT_LANG", "en")
        self.PDF_DEFAULT_DEVICE = os.getenv("PDF_DEFAULT_DEVICE", "cuda")

        # Create directories
        self.DATA_DIR.mkdir(exist_ok=True)
        self.PDF_DIR.mkdir(exist_ok=True)
        self.MARKDOWN_DIR.mkdir(exist_ok=True)

    def load_prompt(self, prompt_name: str) -> str:
        """Load a prompt from the prompts directory"""
        prompt_path = self.PROMPTS_DIR / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")


class DeepSeekClient:
    """Client for interacting with DeepSeek API (OpenAI-compatible)"""

    def __init__(self, config: Config):
        self.config = config
        if AsyncOpenAI is None:
            raise ImportError("openai package is required. Install with: pip install openai")
        self.client = AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_API_BASE
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send chat completion request to DeepSeek API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature or self.config.TEMPERATURE,
                max_tokens=max_tokens or self.config.MAX_TOKENS,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise


class LangfuseClient:
    """Wrapper for Langfuse observability (optional)"""

    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.LANGFUSE_ENABLED and Langfuse is not None

        if self.enabled:
            try:
                self.client = Langfuse(
                    public_key=config.LANGFUSE_PUBLIC_KEY,
                    secret_key=config.LANGFUSE_SECRET_KEY,
                    host=config.LANGFUSE_HOST,
                )
                logger.info("Langfuse observability enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self.enabled = False
        else:
            logger.info("Langfuse observability disabled")

    def trace(self, name: str, metadata: Dict = None):
        """Create a trace (if enabled)"""
        if self.enabled and langfuse_context:
            return langfuse_context.update_current_trace(
                name=name,
                metadata=metadata or {}
            )
        return None

    def span(self, name: str, input_data: Any = None, metadata: Dict = None):
        """Create a span (if enabled)"""
        if self.enabled and langfuse_context:
            return langfuse_context.update_current_observation(
                name=name,
                input=input_data,
                metadata=metadata or {}
            )
        return None


class MainAgent:
    """Main Agent - Planning and Report Generation"""

    def __init__(self, config: Config, deepseek: DeepSeekClient, langfuse: LangfuseClient):
        self.config = config
        self.deepseek = deepseek
        self.langfuse = langfuse

        # Load prompts
        self.planning_prompt = config.load_prompt("main_agent_planning")
        self.report_prompt = config.load_prompt("main_agent_report")

    async def plan(self, user_request: str, available_files: Dict[str, List[str]]) -> Dict:
        """
        Planning phase: Analyze user request and create execution plan

        Args:
            user_request: Natural language request from user
            available_files: Dict with keys 'tabular', 'sensor', 'pdf' and lists of file paths

        Returns:
            plan_json: Structured plan indicating which sub-agents to call
        """
        logger.info("Main Agent: Planning phase started")

        # Build the user message
        files_str = json.dumps(available_files, indent=2)
        user_message = f"""
User Request:
{user_request}

Available Files:
{files_str}

Create a plan following the output format specified.
"""

        messages = [
            {"role": "system", "content": self.planning_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            # Call DeepSeek API
            response = await self.deepseek.chat_completion(messages)

            # Parse JSON from response
            # DeepSeek might include reasoning, so extract JSON
            plan_json = self._extract_json(response)

            logger.success(f"Main Agent: Plan created - {plan_json.get('report_type', 'Unknown')}")
            return plan_json

        except Exception as e:
            logger.error(f"Main Agent planning failed: {e}")
            raise

    async def generate_report(self, user_request: str, structured_data: Dict) -> str:
        """
        Report generation phase: Synthesize structured data into final report

        Args:
            user_request: Original user request
            structured_data: Combined JSON output from all sub-agents

        Returns:
            final_report: Natural language medical report
        """
        logger.info("Main Agent: Report generation phase started")

        # Build the user message
        data_str = json.dumps(structured_data, indent=2, ensure_ascii=False)
        user_message = f"""
Original User Request:
{user_request}

Structured Data from Sub-Agents:
{data_str}

Generate a comprehensive medical report based on this data.
"""

        messages = [
            {"role": "system", "content": self.report_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            # Call DeepSeek API
            response = await self.deepseek.chat_completion(
                messages,
                temperature=0.7,
                max_tokens=8192  # Allow longer output for reports
            )

            logger.success("Main Agent: Report generated successfully")
            return response

        except Exception as e:
            logger.error(f"Main Agent report generation failed: {e}")
            raise

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from text that may contain reasoning or other content"""
        # Try to find JSON in code blocks first
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            json_str = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            json_str = text[start:end].strip()
        else:
            # Try to find JSON object directly
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
            else:
                json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Attempted to parse: {json_str[:500]}")
            raise ValueError(f"Could not extract valid JSON from response: {e}")


class PDFAgent:
    """PDF/Text Sub-Agent - Extracts structured data from PDF documents"""

    def __init__(self, config: Config, deepseek: DeepSeekClient, langfuse: LangfuseClient):
        self.config = config
        self.deepseek = deepseek
        self.langfuse = langfuse
        self.prompt = config.load_prompt("pdf_agent")

    async def process(self, pdf_files: List[str]) -> Dict:
        """
        Process PDF files and extract structured medical data

        Args:
            pdf_files: List of PDF file paths

        Returns:
            Structured JSON with extracted medical data
        """
        logger.info(f"PDF Agent: Processing {len(pdf_files)} PDF files")

        all_extractions = []

        for pdf_file in pdf_files:
            try:
                # Step 1: Convert PDF to Markdown using pdf_to_markdown.py
                markdown_content = await self._pdf_to_markdown(pdf_file)

                # Step 2: Extract structured data from markdown using LLM
                extracted_data = await self._extract_from_markdown(markdown_content, pdf_file)

                all_extractions.append(extracted_data)

            except Exception as e:
                logger.error(f"PDF Agent: Failed to process {pdf_file}: {e}")
                # Continue with other files
                all_extractions.append({
                    "error": str(e),
                    "source_file": pdf_file,
                    "status": "failed"
                })

        # Combine all extractions
        result = {
            "pdf_agent_results": all_extractions,
            "total_processed": len(pdf_files),
            "successful": len([x for x in all_extractions if "error" not in x])
        }

        logger.success(f"PDF Agent: Processed {result['successful']}/{len(pdf_files)} files successfully")
        return result

    async def _pdf_to_markdown(self, pdf_path: str) -> str:
        """Convert PDF to Markdown using pdf_to_markdown.py script"""
        logger.info(f"Converting PDF to Markdown: {pdf_path}")

        # Build command
        cmd = [
            "python",
            str(self.config.PDF_TO_MARKDOWN_SCRIPT),
            pdf_path,
            "--device", self.config.PDF_DEFAULT_DEVICE,
            "--lang", self.config.PDF_DEFAULT_LANG,
        ]

        # Run subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"PDF to Markdown conversion failed: {error_msg}")

        # Parse output to get markdown file path
        output = stdout.decode()

        # The script prints "Markdown file created: <path>" or returns the path
        markdown_path = self._extract_markdown_path(output, pdf_path)

        if not markdown_path or not Path(markdown_path).exists():
            raise FileNotFoundError(f"Markdown file not found after conversion: {markdown_path}")

        # Read markdown content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.success(f"PDF converted to Markdown: {markdown_path}")
        return content

    def _extract_markdown_path(self, output: str, pdf_path: str) -> str:
        """Extract markdown file path from conversion script output"""
        # Look for "Markdown file created:" or "Success! Markdown saved to:"
        for line in output.split('\n'):
            if 'Markdown file' in line or 'Success!' in line:
                # Extract path after the colon
                if ':' in line:
                    path = line.split(':', 1)[1].strip()
                    return path

        # Fallback: guess the path based on pdf_to_markdown.py logic
        pdf_name = Path(pdf_path).stem
        markdown_path = self.config.MARKDOWN_DIR / pdf_name / "auto" / f"{pdf_name}.md"
        return str(markdown_path)

    async def _extract_from_markdown(self, markdown_content: str, source_file: str) -> Dict:
        """Extract structured data from markdown content using LLM"""
        logger.info(f"Extracting structured data from markdown: {source_file}")

        user_message = f"""
Source File: {source_file}

Markdown Content:
{markdown_content}

Extract structured medical data following the output format specified.
"""

        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.deepseek.chat_completion(messages, temperature=0.3)
            extracted_data = self._extract_json(response)
            return extracted_data

        except Exception as e:
            logger.error(f"Failed to extract data from markdown: {e}")
            raise

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from text (same as MainAgent)"""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            json_str = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            json_str = text[start:end].strip()
        else:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
            else:
                json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Could not extract valid JSON from response: {e}")


class TabularAgent:
    """Tabular Sub-Agent - PLACEHOLDER for CSV/XLSX processing"""

    def __init__(self, config: Config, deepseek: DeepSeekClient, langfuse: LangfuseClient):
        self.config = config
        self.deepseek = deepseek
        self.langfuse = langfuse
        self.prompt = config.load_prompt("tabular_agent")

    async def process(self, tabular_files: List[str]) -> Dict:
        """
        Process tabular files - PLACEHOLDER

        Args:
            tabular_files: List of CSV/XLSX file paths

        Returns:
            Structured JSON (placeholder response for now)
        """
        logger.warning(f"Tabular Agent: PLACEHOLDER - Processing {len(tabular_files)} files")

        # TODO: Implement actual tabular data processing
        # For now, return a placeholder response
        return {
            "tabular_agent_results": [],
            "status": "placeholder",
            "message": "Tabular agent not yet implemented",
            "files_received": tabular_files
        }


class SensorAgent:
    """Sensor Sub-Agent - PLACEHOLDER for time-series data processing"""

    def __init__(self, config: Config, deepseek: DeepSeekClient, langfuse: LangfuseClient):
        self.config = config
        self.deepseek = deepseek
        self.langfuse = langfuse
        self.prompt = config.load_prompt("sensor_agent")

    async def process(self, sensor_files: List[str]) -> Dict:
        """
        Process sensor/time-series files - PLACEHOLDER

        Args:
            sensor_files: List of sensor data file paths

        Returns:
            Structured JSON (placeholder response for now)
        """
        logger.warning(f"Sensor Agent: PLACEHOLDER - Processing {len(sensor_files)} files")

        # TODO: Implement actual sensor data processing
        # For now, return a placeholder response
        return {
            "sensor_agent_results": [],
            "status": "placeholder",
            "message": "Sensor agent not yet implemented",
            "files_received": sensor_files
        }


class Orchestrator:
    """
    Orchestrator - Coordinates the multi-agent workflow

    Workflow:
    1. Main Agent creates a plan
    2. Orchestrator calls relevant sub-agents in parallel
    3. Orchestrator combines sub-agent outputs
    4. Main Agent generates final report
    """

    def __init__(self, config: Config):
        self.config = config
        self.deepseek = DeepSeekClient(config)
        self.langfuse = LangfuseClient(config)

        # Initialize agents
        self.main_agent = MainAgent(config, self.deepseek, self.langfuse)
        self.pdf_agent = PDFAgent(config, self.deepseek, self.langfuse)
        self.tabular_agent = TabularAgent(config, self.deepseek, self.langfuse)
        self.sensor_agent = SensorAgent(config, self.deepseek, self.langfuse)

    async def run(self, user_request: str, available_files: Dict[str, List[str]]) -> Dict:
        """
        Run the complete multi-agent workflow

        Args:
            user_request: Natural language request from user
            available_files: Dict with keys 'tabular', 'sensor', 'pdf' and lists of file paths

        Returns:
            Dict containing plan, structured_data, and final_report
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("ORCHESTRATOR: Starting multi-agent workflow")
        logger.info("=" * 80)

        try:
            # Step 1: Main Agent - Planning
            logger.info("\n[STEP 1] Main Agent - Planning Phase")
            plan = await self.main_agent.plan(user_request, available_files)
            logger.info(f"Plan: {json.dumps(plan, indent=2)}")

            # Step 2: Call Sub-Agents in Parallel
            logger.info("\n[STEP 2] Calling Sub-Agents in Parallel")
            sub_agent_tasks = []

            if plan.get("need_pdf") and plan.get("files", {}).get("pdf"):
                logger.info(f"  → PDF Agent will process {len(plan['files']['pdf'])} files")
                sub_agent_tasks.append(("pdf", self.pdf_agent.process(plan["files"]["pdf"])))

            if plan.get("need_tabular") and plan.get("files", {}).get("tabular"):
                logger.info(f"  → Tabular Agent will process {len(plan['files']['tabular'])} files")
                sub_agent_tasks.append(("tabular", self.tabular_agent.process(plan["files"]["tabular"])))

            if plan.get("need_sensor") and plan.get("files", {}).get("sensor"):
                logger.info(f"  → Sensor Agent will process {len(plan['files']['sensor'])} files")
                sub_agent_tasks.append(("sensor", self.sensor_agent.process(plan["files"]["sensor"])))

            # Execute sub-agents in parallel
            if sub_agent_tasks:
                results = await asyncio.gather(*[task for _, task in sub_agent_tasks], return_exceptions=True)

                # Combine results
                structured_data = {}
                for (agent_type, _), result in zip(sub_agent_tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"{agent_type.upper()} Agent failed: {result}")
                        structured_data[agent_type] = {"error": str(result), "status": "failed"}
                    else:
                        structured_data[agent_type] = result
            else:
                logger.warning("No sub-agents were called (no relevant data in plan)")
                structured_data = {}

            logger.success("\n[STEP 2 COMPLETE] Sub-agents finished")

            # Step 3: Main Agent - Generate Final Report
            logger.info("\n[STEP 3] Main Agent - Report Generation Phase")
            final_report = await self.main_agent.generate_report(user_request, structured_data)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            logger.success("\n" + "=" * 80)
            logger.success(f"ORCHESTRATOR: Workflow completed in {execution_time:.2f} seconds")
            logger.success("=" * 80)

            return {
                "plan": plan,
                "structured_data": structured_data,
                "final_report": final_report,
                "execution_time_seconds": execution_time,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Orchestrator workflow failed: {e}")
            raise


# Convenience function for easy usage
async def generate_medical_report(
    user_request: str,
    pdf_files: List[str] = None,
    tabular_files: List[str] = None,
    sensor_files: List[str] = None,
    config: Config = None
) -> Dict:
    """
    Convenience function to generate a medical report

    Args:
        user_request: Natural language description of the desired report
        pdf_files: List of PDF file paths
        tabular_files: List of CSV/XLSX file paths
        sensor_files: List of sensor data file paths
        config: Optional custom configuration

    Returns:
        Dict with plan, structured_data, and final_report
    """
    if config is None:
        config = Config()

    available_files = {
        "pdf": pdf_files or [],
        "tabular": tabular_files or [],
        "sensor": sensor_files or []
    }

    orchestrator = Orchestrator(config)
    return await orchestrator.run(user_request, available_files)
