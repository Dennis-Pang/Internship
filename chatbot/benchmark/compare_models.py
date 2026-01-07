#!/usr/bin/env python3
"""
Compare LLM benchmark results across multiple models
Generates bar chart and radar chart for 12 evaluation metrics
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Metrics to evaluate (12 total)
METRICS = [
    'persona_consistency',
    'emotional_congruence',
    'memory_utilization',
    'relevance',
    'coherence',
    'helpfulness',
    'empathy',
    'politeness',
    'safety',
    'logical_consistency',
    'conversational_continuity',
    'groundedness'
]

# Metric display names (for charts)
METRIC_LABELS = [
    'Persona\nConsistency',
    'Emotional\nCongruence',
    'Memory\nUtilization',
    'Relevance',
    'Coherence',
    'Helpfulness',
    'Empathy',
    'Politeness',
    'Safety',
    'Logical\nConsistency',
    'Conversational\nContinuity',
    'Groundedness'
]

# Model configurations
MODELS = {
    'gemma3_4b': {
        'file': 'results/gemma3_4b_100.csv',
        'display_name': 'Gemma3 4B',
        'color': '#1E88E5'  # Blue
    },
    'phi3_3.8b': {
        'file': 'results/phi3_3.8b_100.csv',
        'display_name': 'Phi3 3.8B',
        'color': '#43A047'  # Green
    },
    'qwen2.5_3b': {
        'file': 'results/qwen2.5_3b-instruct_100.csv',
        'display_name': 'Qwen2.5 3B',
        'color': '#E53935'  # Red
    }
}


def load_model_results(model_key):
    """Load CSV results for a model and calculate mean scores"""
    file_path = Path(MODELS[model_key]['file'])

    if not file_path.exists():
        print(f"Warning: {file_path} not found, skipping {model_key}")
        return None

    df = pd.read_csv(file_path)

    # Calculate mean for each metric
    means = {}
    for metric in METRICS:
        if metric in df.columns:
            means[metric] = df[metric].mean()
        else:
            print(f"Warning: Metric '{metric}' not found in {file_path}")
            means[metric] = 0.0

    return means


def plot_bar_chart(results, output_path='results/comparison_bar.png'):
    """Generate grouped bar chart comparing all metrics"""
    fig, ax = plt.subplots(figsize=(16, 8))

    x = np.arange(len(METRICS))
    width = 0.25

    # Plot bars for each model
    for i, (model_key, model_info) in enumerate(MODELS.items()):
        if model_key not in results:
            continue

        scores = [results[model_key][metric] for metric in METRICS]
        offset = width * (i - 1)
        ax.bar(x + offset, scores, width,
               label=model_info['display_name'],
               color=model_info['color'],
               alpha=0.8)

    # Formatting
    ax.set_xlabel('Metrics', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('LLM Benchmark Comparison: 12 Metrics (100 Samples)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(METRIC_LABELS, rotation=45, ha='right', fontsize=9)
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, 1.1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Bar chart saved to {output_path}")
    plt.close()


def plot_radar_chart(results, output_path='results/comparison_radar.png'):
    """Generate radar chart comparing all metrics"""
    fig, ax = plt.subplots(figsize=(12, 12), subplot_kw=dict(projection='polar'))

    # Number of metrics
    num_metrics = len(METRICS)
    angles = np.linspace(0, 2 * np.pi, num_metrics, endpoint=False).tolist()

    # Close the plot by appending the first angle
    angles += angles[:1]

    # Plot each model
    for model_key, model_info in MODELS.items():
        if model_key not in results:
            continue

        scores = [results[model_key][metric] for metric in METRICS]
        scores += scores[:1]  # Close the plot

        ax.plot(angles, scores, 'o-', linewidth=2,
                label=model_info['display_name'],
                color=model_info['color'])
        ax.fill(angles, scores, alpha=0.15, color=model_info['color'])

    # Formatting
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(METRIC_LABELS, fontsize=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=9)
    ax.grid(True, linestyle='--', alpha=0.6)

    plt.title('LLM Benchmark Radar Chart: 12 Metrics (100 Samples)',
              fontsize=14, fontweight='bold', pad=30)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Radar chart saved to {output_path}")
    plt.close()


def print_summary_table(results):
    """Print formatted comparison table to console"""
    print("\n" + "="*80)
    print("BENCHMARK COMPARISON SUMMARY (100 Samples)")
    print("="*80)
    print(f"{'Metric':<30} {'Gemma3 4B':<15} {'Phi3 3.8B':<15} {'Qwen2.5 3B':<15}")
    print("-"*80)

    for metric, label in zip(METRICS, METRIC_LABELS):
        label_clean = label.replace('\n', ' ')
        scores = []
        for model_key in MODELS.keys():
            if model_key in results:
                score = results[model_key][metric]
                scores.append(f"{score:.4f}")
            else:
                scores.append("N/A")

        print(f"{label_clean:<30} {scores[0]:<15} {scores[1]:<15} {scores[2]:<15}")

    print("-"*80)

    # Calculate overall averages
    print(f"{'OVERALL AVERAGE':<30}", end="")
    for model_key in MODELS.keys():
        if model_key in results:
            avg = np.mean([results[model_key][m] for m in METRICS])
            print(f"{avg:.4f}{' '*10}", end="")
        else:
            print(f"{'N/A':<15}", end="")
    print()
    print("="*80 + "\n")


def main():
    """Main comparison workflow"""
    print("Loading model results...")

    # Load results for all models
    results = {}
    for model_key in MODELS.keys():
        model_results = load_model_results(model_key)
        if model_results:
            results[model_key] = model_results
            print(f"  ✓ Loaded {MODELS[model_key]['display_name']}")

    if not results:
        print("Error: No valid model results found!")
        return

    print(f"\nLoaded {len(results)} models successfully\n")

    # Generate visualizations
    print("Generating visualizations...")
    plot_bar_chart(results)
    plot_radar_chart(results)

    # Print summary table
    print_summary_table(results)

    print("✓ Comparison complete!")


if __name__ == '__main__':
    main()
