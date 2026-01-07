"""Metrics modules for benchmark evaluation.

Each metric is implemented in a separate module:
- memory_utilization.py: Memory Utilization Accuracy (precision/recall/F1)
- groundedness.py: Groundedness / Hallucination Rate evaluation
- relevance.py: Response Relevance using OpenAI embeddings (cosine similarity)
- coherence.py: Response Coherence using LLM rubric scoring (1-5 scale)
- emotional_congruence.py: Emotional Congruence / Tone alignment (1-5 scale)
- helpfulness.py: Helpfulness / Task effectiveness and actionability (1-5 scale)
- persona_consistency.py: Persona Consistency / Personality alignment (1-5 scale)
- safety.py: Safety / Toxicity (0-1 safety score)
- politeness.py: Politeness / Social acceptability (0-1 politeness score)
- conversational_continuity.py: Conversational Continuity / Dialogue coherence (0-1 scale)
- logical_consistency.py: Logical Consistency / Reasoning quality (1-5 scale)
- empathy.py: Empathy Score / Emotional intelligence and warmth (1-5 scale)
"""

from .memory_utilization import (
    MemoryUtilizationJudgment,
    judge_memory_utilization,
    calculate_sample_metrics,
)

from .groundedness import (
    FactualClaim,
    GroundednessJudgment,
    judge_groundedness,
)

from .relevance import (
    judge_relevance,
    RelevanceJudgment,
)

from .coherence import (
    CoherenceJudgment,
    judge_coherence,
)

from .emotional_congruence import (
    EmotionalCongruenceJudgment,
    judge_emotional_congruence,
)

from .logical_consistency import (
    LogicalConsistencyJudgment,
    Contradiction,
    judge_logical_consistency,
)

from .empathy import (
    EmpathyJudgment,
    judge_empathy,
)

from .helpfulness import (
    HelpfulnessJudgment,
    judge_helpfulness,
)

from .persona_consistency import (
    PersonaConsistencyJudgment,
    judge_persona_consistency,
)

from .safety import (
    SafetyJudgment,
    judge_safety,
)

from .politeness import (
    PolitenessJudgment,
    judge_politeness,
)

from .conversational_continuity import (
    ContinuityJudgment,
    judge_conversational_continuity,
)

__all__ = [
    # Memory Utilization
    "MemoryUtilizationJudgment",
    "judge_memory_utilization",
    "calculate_sample_metrics",
    # Groundedness
    "FactualClaim",
    "GroundednessJudgment",
    "judge_groundedness",
    # Relevance
    "judge_relevance",
    "RelevanceJudgment",
    # Coherence
    "CoherenceJudgment",
    "judge_coherence",
    # Emotional Congruence
    "EmotionalCongruenceJudgment",
    "judge_emotional_congruence",
    # Logical Consistency
    "LogicalConsistencyJudgment",
    "Contradiction",
    "judge_logical_consistency",
    # Empathy
    "EmpathyJudgment",
    "judge_empathy",
    # Helpfulness
    "HelpfulnessJudgment",
    "judge_helpfulness",
    # Persona Consistency
    "PersonaConsistencyJudgment",
    "judge_persona_consistency",
    # Safety
    "SafetyJudgment",
    "judge_safety",
    # Politeness / Social Acceptability
    "PolitenessJudgment",
    "judge_politeness",
    # Conversational Continuity
    "ContinuityJudgment",
    "judge_conversational_continuity",
]
