#!/usr/bin/env python3
"""
Generate a simple comparison TXT file with average scores for all models.
"""

import pandas as pd
from pathlib import Path


def generate_comparison_txt():
    """Generate simple comparison TXT with average scores."""
    results_dir = Path(__file__).parent / "results"

    # Find all CSV files
    csv_files = sorted([f for f in results_dir.glob("*.csv") if "_summary" not in f.name])

    if not csv_files:
        print("No CSV files found.")
        return

    # Metric names in order
    metric_names = [
        "persona_consistency",
        "emotional_congruence",
        "memory_utilization",
        "relevance",
        "coherence",
        "helpfulness",
        "empathy",
        "politeness",
        "safety",
        "logical_consistency",
        "conversational_continuity",
        "groundedness",
    ]

    # Pretty names for display
    metric_display_names = {
        "persona_consistency": "Persona Consistency",
        "emotional_congruence": "Emotional Congruence",
        "memory_utilization": "Memory Utilization (F1)",
        "relevance": "Relevance",
        "coherence": "Coherence",
        "helpfulness": "Helpfulness",
        "empathy": "Empathy",
        "politeness": "Politeness",
        "safety": "Safety",
        "logical_consistency": "Logical Consistency",
        "conversational_continuity": "Conversational Continuity",
        "groundedness": "Groundedness",
    }

    # Collect data from all CSVs
    model_scores = {}
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        model_name = csv_file.stem.rsplit('_', 1)[0]  # Remove _100 suffix

        scores = {}
        for metric in metric_names:
            if metric in df.columns:
                scores[metric] = df[metric].mean()

        model_scores[model_name] = scores

    # Generate output
    output_file = results_dir / "model_comparison.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("MODEL COMPARISON - AVERAGE SCORES\n")
        f.write("=" * 100 + "\n\n")

        # Header row
        models = list(model_scores.keys())
        f.write(f"{'Metric':<40}")
        for model in models:
            f.write(f"{model:>20}")
        f.write("\n")
        f.write("-" * 100 + "\n")

        # Data rows
        for metric in metric_names:
            display_name = metric_display_names.get(metric, metric)
            f.write(f"{display_name:<40}")
            for model in models:
                score = model_scores[model].get(metric, 0.0)
                f.write(f"{score:>20.4f}")
            f.write("\n")

        # Overall average row
        f.write("-" * 100 + "\n")
        f.write(f"{'OVERALL AVERAGE':<40}")
        for model in models:
            avg_score = sum(model_scores[model].values()) / len(metric_names)
            f.write(f"{avg_score:>20.4f}")
        f.write("\n")

        f.write("=" * 100 + "\n")

    print(f"✓ Generated: {output_file}")
    return output_file


if __name__ == "__main__":
    generate_comparison_txt()
