"""LLM Router for Multi-Provider Support.

This module provides a unified interface for calling LLMs from different providers:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini)
- Ollama (local models)

Supports both completion and embedding endpoints with structured output via instructor.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from enum import Enum

import instructor
from pydantic import BaseModel

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.config import logger


# ============================================================================
# Provider Enums
# ============================================================================

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    OLLAMA = "ollama"


# ============================================================================
# LLM Client Factory
# ============================================================================

def get_llm_client(provider: str):
    """Get LLM client for specified provider.

    Args:
        provider: Provider name (anthropic/openai/google/ollama)

    Returns:
        Initialized client instance

    Raises:
        ValueError: If provider is not supported
        ImportError: If provider SDK is not installed
    """
    provider = provider.lower()

    if provider == LLMProvider.ANTHROPIC:
        try:
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            return Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    elif provider == LLMProvider.OPENAI:
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            return OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    elif provider == LLMProvider.GOOGLE:
        try:
            from google import genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            return genai.Client(api_key=api_key)
        except ImportError:
            raise ImportError("google-genai package not installed. Run: pip install google-genai")

    elif provider == LLMProvider.OLLAMA:
        try:
            from openai import OpenAI
            # Ollama uses OpenAI-compatible API
            return OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama"  # Dummy key
            )
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    else:
        raise ValueError(f"Unsupported provider: {provider}. Must be one of: {[p.value for p in LLMProvider]}")


# ============================================================================
# Structured Output with Instructor
# ============================================================================

def get_structured_response(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    response_model: Type[BaseModel],
    temperature: float = 0.0,
    max_tokens: Optional[int] = None,
) -> BaseModel:
    """Get structured response from LLM using instructor.

    Args:
        provider: LLM provider (anthropic/openai/google/ollama)
        model: Model name (e.g., "claude-3-5-sonnet-20241022", "gpt-4o", "gemini-2.0-flash-exp")
        messages: Chat messages in OpenAI format [{"role": "user", "content": "..."}]
        response_model: Pydantic model class for structured output
        temperature: Sampling temperature (0.0 = deterministic)
        max_tokens: Maximum tokens to generate

    Returns:
        Pydantic model instance with structured response

    Raises:
        ValueError: If provider is not supported
        Exception: If API call fails
    """
    provider = provider.lower()

    try:
        if provider == LLMProvider.ANTHROPIC:
            # Anthropic uses native instructor support
            client = get_llm_client(provider)
            instructor_client = instructor.from_anthropic(client)

            # Convert messages to Anthropic format
            anthropic_messages = []
            system_message = None

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            # Call with instructor
            kwargs = {
                "model": model,
                "messages": anthropic_messages,
                "response_model": response_model,
                "temperature": temperature,
            }
            if system_message:
                kwargs["system"] = system_message
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            return instructor_client.messages.create(**kwargs)

        elif provider == LLMProvider.OPENAI:
            # OpenAI uses instructor patching
            client = get_llm_client(provider)
            instructor_client = instructor.from_openai(client)

            kwargs = {
                "model": model,
                "messages": messages,
                "response_model": response_model,
                "temperature": temperature,
            }
            if max_tokens:
                # GPT-5.2 and newer models require max_completion_tokens instead of max_tokens
                if "gpt-5" in model.lower() or "o1" in model.lower() or "o3" in model.lower():
                    kwargs["max_completion_tokens"] = max_tokens
                else:
                    kwargs["max_tokens"] = max_tokens

            return instructor_client.chat.completions.create(**kwargs)

        elif provider == LLMProvider.GOOGLE:
            # Google Gemini - use native Pydantic JSON schema support
            client = get_llm_client(provider)

            # Combine messages into single prompt
            prompt = "\n\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in messages])

            # Generate content with JSON schema
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": response_model.model_json_schema(),
                    "temperature": temperature,
                },
            )

            # Parse JSON response into Pydantic model
            return response_model.model_validate_json(response.text)

        elif provider == LLMProvider.OLLAMA:
            # Ollama uses OpenAI-compatible API with instructor
            client = get_llm_client(provider)
            instructor_client = instructor.from_openai(client, mode=instructor.Mode.JSON)

            kwargs = {
                "model": model,
                "messages": messages,
                "response_model": response_model,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            return instructor_client.chat.completions.create(**kwargs)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    except Exception as e:
        logger.error(f"LLM call failed for {provider}/{model}: {e}")
        raise


# ============================================================================
# Helper Functions
# ============================================================================

def validate_provider_model(provider: str, model: str) -> bool:
    """Validate that provider and model combination is valid.

    Args:
        provider: Provider name
        model: Model name

    Returns:
        True if valid, raises ValueError otherwise
    """
    provider = provider.lower()

    # Common model prefixes/patterns by provider
    provider_patterns = {
        LLMProvider.ANTHROPIC: ["claude"],
        LLMProvider.OPENAI: ["gpt", "o1", "o3"],
        LLMProvider.GOOGLE: ["gemini", "models/gemini"],
        LLMProvider.OLLAMA: [],  # Any model name is valid for Ollama
    }

    if provider not in [p.value for p in LLMProvider]:
        raise ValueError(f"Unknown provider: {provider}")

    if provider == LLMProvider.OLLAMA:
        return True  # Ollama accepts any model name

    patterns = provider_patterns.get(provider, [])
    if not any(pattern in model.lower() for pattern in patterns):
        logger.warning(
            f"Model '{model}' does not match expected pattern for provider '{provider}'. "
            f"Expected patterns: {patterns}"
        )

    return True


# ============================================================================
# Configuration Helpers
# ============================================================================

def get_default_model(provider: str) -> str:
    """Get default model for provider.

    Args:
        provider: Provider name

    Returns:
        Default model name for that provider
    """
    defaults = {
        LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.GOOGLE: "gemini-2.0-flash-exp",
        LLMProvider.OLLAMA: "gemma3:4b",
    }
    return defaults.get(provider.lower(), "")


def get_default_embedding_model(provider: str) -> str:
    """Get default embedding model for provider.

    Args:
        provider: Provider name

    Returns:
        Default embedding model name
    """
    defaults = {
        LLMProvider.OPENAI: "text-embedding-3-small",
        LLMProvider.GOOGLE: "models/text-embedding-004",
        LLMProvider.OLLAMA: "nomic-embed-text",
    }
    return defaults.get(provider.lower(), "")
