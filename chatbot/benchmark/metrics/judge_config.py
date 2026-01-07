"""Optimized Judge Model Configuration.

Based on LMArena leaderboard (Dec 2025 - Jan 2026) and benchmark analysis:
- Gemini 3 Pro: #1 overall (1501 Elo), best reasoning (GPQA 91.9%)
- Claude Opus 4.5: #1 coding (SWE-bench 80.9%), #1 instruction following
- GPT-5.2: #1 math reasoning (AIME 100%), abstract reasoning (ARC-AGI 52.9%)
- GPT-4o: #1 general knowledge (MMLU 88.7%), best empathy/social cognition (Sage)

Sources:
- LMArena Leaderboard: https://lmarena.ai/leaderboard
- Chatbot Arena Rankings: https://openlm.ai/chatbot-arena/
- AI Model Benchmarks Dec 2025: https://lmcouncil.ai/benchmarks
- LLM-as-a-Judge Guide: https://www.evidentlyai.com/llm-guide/llm-as-a-judge
- GPT-4o vs Claude vs Gemini: https://www.analyticsvidhya.com/blog/2025/01/gpt-4o-claude-3-5-gemini-2-0-which-llm-to-use-and-when/
"""

from typing import Dict, Tuple


# ============================================================================
# Judge Model Configuration by Metric
# ============================================================================

JUDGE_MODELS: Dict[str, Tuple[str, str, str]] = {
    # Format: "metric_name": (provider, model, reason)

    "persona_consistency": (
        "anthropic",
        "claude-opus-4-5",
        "Best instruction following + deep reasoning for personality traits"
    ),

    "emotional_congruence": (
        "openai",
        "gpt-4o",
        "Highest Sentient score for empathy and emotional understanding (Sage benchmark)"
    ),

    "memory_utilization": (
        "anthropic",
        "claude-opus-4-5",
        "Precision in code/logic tasks, best for detecting exact memory references"
    ),

    "coherence": (
        "openai",
        "gpt-4o",
        "Highest MMLU (88.7%), best general language understanding"
    ),

    "helpfulness": (
        "anthropic",
        "claude-opus-4-5",
        "#1 instruction following, best at judging actionability"
    ),

    "empathy": (
        "openai",
        "gpt-4o",
        "GPT-4o-Latest achieves highest Sentient score for emotional intelligence"
    ),

    "politeness": (
        "openai",
        "gpt-4o",
        "Best social cognition and nuanced tone detection"
    ),

    "safety": (
        "anthropic",
        "claude-opus-4-5",
        "Anthropic's focus on AI safety, constitutional AI principles"
    ),

    "logical_consistency": (
        "openai",
        "gpt-5.2",
        "Perfect 100% on AIME 2025, 52.9% on ARC-AGI abstract reasoning"
    ),

    "conversational_continuity": (
        "google",
        "gemini-2.0-flash-exp",
        "#1 overall (1501 Elo), excellent multimodal context understanding"
    ),

    "groundedness": (
        "anthropic",
        "claude-opus-4-5",
        "High precision, low hallucination rate, best for fact-checking"
    ),

    "relevance": (
        "google",
        "gemini-2.0-flash-exp",
        "#1 overall (1501 Elo), best conversational understanding, 5x cheaper than GPT-4o"
    ),
}


# ============================================================================
# Alternative Models (Fallback/Budget Options)
# ============================================================================

BUDGET_MODELS: Dict[str, Tuple[str, str]] = {
    # Cheaper alternatives with good performance
    "persona_consistency": ("anthropic", "claude-3-5-sonnet-20241022"),
    "emotional_congruence": ("openai", "gpt-4o-mini"),
    "memory_utilization": ("anthropic", "claude-3-5-sonnet-20241022"),
    "coherence": ("openai", "gpt-4o-mini"),
    "helpfulness": ("anthropic", "claude-3-5-sonnet-20241022"),
    "empathy": ("openai", "gpt-4o-mini"),
    "politeness": ("openai", "gpt-4o-mini"),
    "safety": ("anthropic", "claude-3-5-sonnet-20241022"),
    "logical_consistency": ("openai", "gpt-4o-mini"),
    "conversational_continuity": ("google", "gemini-2.0-flash-exp"),
    "groundedness": ("anthropic", "claude-3-5-sonnet-20241022"),
    "relevance": ("google", "gemini-2.0-flash-exp"),  # Already budget-friendly
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_judge_model(metric: str, use_budget: bool = False) -> Tuple[str, str]:
    """Get recommended judge model for a metric.

    Args:
        metric: Metric name
        use_budget: If True, use cheaper alternative models

    Returns:
        (provider, model) tuple

    Raises:
        ValueError: If metric is not recognized
    """
    if metric not in JUDGE_MODELS:
        raise ValueError(f"Unknown metric: {metric}. Available: {list(JUDGE_MODELS.keys())}")

    if use_budget:
        return BUDGET_MODELS.get(metric, JUDGE_MODELS[metric][:2])

    return JUDGE_MODELS[metric][:2]


def get_judge_reason(metric: str) -> str:
    """Get reason why a model was chosen as judge.

    Args:
        metric: Metric name

    Returns:
        Explanation string
    """
    if metric not in JUDGE_MODELS:
        return "Unknown metric"

    return JUDGE_MODELS[metric][2]


def get_all_judge_models(use_budget: bool = False) -> Dict[str, Tuple[str, str]]:
    """Get all judge models for batch evaluation.

    Args:
        use_budget: If True, use cheaper alternative models

    Returns:
        Dictionary mapping metric names to (provider, model) tuples
    """
    if use_budget:
        return BUDGET_MODELS.copy()

    return {metric: (provider, model) for metric, (provider, model, _) in JUDGE_MODELS.items()}


def print_judge_configuration(use_budget: bool = False):
    """Print current judge model configuration.

    Args:
        use_budget: If True, show budget models
    """
    mode = "BUDGET" if use_budget else "OPTIMAL"
    print(f"\n{'='*80}")
    print(f"JUDGE MODEL CONFIGURATION ({mode} MODE)")
    print(f"{'='*80}\n")

    models = BUDGET_MODELS if use_budget else JUDGE_MODELS

    for metric in sorted(models.keys()):
        if use_budget:
            provider, model = models[metric]
            reason = "Budget alternative"
        else:
            provider, model, reason = models[metric]

        print(f"{metric}:")
        print(f"  Provider: {provider}")
        print(f"  Model:    {model}")
        print(f"  Reason:   {reason}")
        print()


# ============================================================================
# Cost Estimation
# ============================================================================

PRICING_PER_1M_TOKENS = {
    # Format: (provider, model): (input_price, output_price)
    ("openai", "gpt-4o"): (2.50, 10.00),
    ("openai", "gpt-4o-mini"): (0.15, 0.60),
    ("openai", "gpt-5.2"): (5.00, 15.00),  # Estimated
    ("anthropic", "claude-opus-4-5"): (15.00, 75.00),  # Estimated
    ("anthropic", "claude-3-5-sonnet-20241022"): (3.00, 15.00),
    ("google", "gemini-2.0-flash-exp"): (0.00, 0.00),  # Free tier
    ("google", "gemini-3-pro"): (3.50, 10.50),  # Estimated
    ("openai", "text-embedding-3-small"): (0.02, 0.00),
}


def estimate_cost(
    num_samples: int = 100,
    avg_tokens_per_metric: int = 500,
    use_budget: bool = False
) -> float:
    """Estimate total evaluation cost.

    Args:
        num_samples: Number of samples to evaluate
        avg_tokens_per_metric: Average tokens per metric evaluation
        use_budget: If True, use budget models for estimation

    Returns:
        Estimated cost in USD
    """
    models = get_all_judge_models(use_budget)
    total_cost = 0.0

    for metric, (provider, model) in models.items():
        if metric == "relevance":
            # Embedding cost
            pricing = PRICING_PER_1M_TOKENS.get((provider, model), (0.02, 0.0))
            # Assume 2 embeddings per sample (query + response)
            cost = (num_samples * 2 * avg_tokens_per_metric / 1_000_000) * pricing[0]
        else:
            # LLM judge cost
            pricing = PRICING_PER_1M_TOKENS.get((provider, model))
            if pricing is None:
                continue  # Skip if pricing not available

            input_cost = (num_samples * avg_tokens_per_metric / 1_000_000) * pricing[0]
            output_cost = (num_samples * 200 / 1_000_000) * pricing[1]  # ~200 tokens output
            cost = input_cost + output_cost

        total_cost += cost

    return total_cost


if __name__ == "__main__":
    # Print optimal configuration
    print_judge_configuration(use_budget=False)

    # Print budget configuration
    print_judge_configuration(use_budget=True)

    # Estimate costs
    print(f"{'='*80}")
    print("COST ESTIMATION (100 samples)")
    print(f"{'='*80}\n")
    optimal_cost = estimate_cost(100, use_budget=False)
    budget_cost = estimate_cost(100, use_budget=True)
    print(f"Optimal judges: ${optimal_cost:.2f}")
    print(f"Budget judges:  ${budget_cost:.2f}")
    print(f"Savings:        ${optimal_cost - budget_cost:.2f} ({100 * (1 - budget_cost/optimal_cost):.1f}%)\n")
