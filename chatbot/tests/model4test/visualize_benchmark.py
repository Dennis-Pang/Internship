#!/usr/bin/env python3
"""
Benchmark Visualization Tool for Model Evaluation Results
Academic style with 2 bar charts: Performance metrics + Total latency
"""

import matplotlib.pyplot as plt
import numpy as np

# Academic style settings
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['grid.linewidth'] = 0.8

# Data from evl_result.md
models = ['llama3.1:8b', 'mistral:7b-instruct', 'qwen2.5:7b-instruct']
models_short = ['llama3.1:8b', 'mistral:7b-instruct', 'qwen2.5:7b-instruct']

# Performance metrics (excluding LLM Judge)
precision = [0.377, 0.453, 0.592]
recall = [0.580, 0.480, 0.900]
f1 = [0.457, 0.466, 0.714]

# Total latency (seconds)
latency_total = [2302.072, 1291.940, 1749.467]

# Academic color palette (colorblind-friendly)
colors = ['#4477AA', '#EE6677', '#228833']  # Blue, Red, Green

# Create figure with 2 subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

# ==================== Performance Metrics Bar Chart ====================
metrics_data = {
    'Precision': precision,
    'Recall': recall,
    'F1 Score': f1
}

x = np.arange(len(models))
width = 0.25
multiplier = 0

for attribute, measurement in metrics_data.items():
    offset = width * (multiplier - 1)
    bars = ax1.bar(x + offset, measurement, width, label=attribute,
                   edgecolor='black', linewidth=0.8, alpha=0.85)

    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{measurement[i]:.3f}',
                ha='center', va='bottom', fontsize=9)
    multiplier += 1

ax1.set_ylabel('Score', fontsize=12, fontweight='bold')
ax1.set_xlabel('Model', fontsize=12, fontweight='bold')
ax1.set_title('(a) Performance Metrics', fontsize=13, fontweight='bold', loc='left')
ax1.set_xticks(x)
ax1.set_xticklabels(models, fontsize=11)
ax1.legend(loc='upper left', fontsize=10, frameon=True, edgecolor='black',
           ncol=2, columnspacing=1)
ax1.set_ylim(0, 1.05)
ax1.grid(axis='y', linestyle='--', alpha=0.4)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# ==================== Total Latency Bar Chart ====================
x2 = np.arange(len(models))

bars = ax2.bar(x2, latency_total, width=0.6, color=colors,
               edgecolor='black', linewidth=1.2, alpha=0.85)

# Add value labels on bars
for i, bar in enumerate(bars):
    height = bar.get_height()
    # Convert to minutes for readability
    minutes = height / 60
    ax2.text(bar.get_x() + bar.get_width()/2., height + 50,
            f'{height:.1f}s\n({minutes:.1f}min)',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

ax2.set_ylabel('Total Time (seconds)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Model', fontsize=12, fontweight='bold')
ax2.set_title('(b) Total Processing Time', fontsize=13, fontweight='bold', loc='left')
ax2.set_xticks(x2)
ax2.set_xticklabels(models, fontsize=11)
ax2.set_ylim(0, max(latency_total) * 1.15)
ax2.grid(axis='y', linestyle='--', alpha=0.4)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

# Add horizontal line for reference (e.g., 30 min = 1800s)
ax2.axhline(y=1800, color='gray', linestyle=':', linewidth=1.5, alpha=0.6)
ax2.text(2.5, 1850, '30 min', fontsize=9, color='gray', style='italic')

# Overall title
fig.suptitle('Model Benchmark Results - Slot Extraction Performance',
             fontsize=14, fontweight='bold', y=0.98)

plt.tight_layout()

# Save figure
plt.savefig('benchmark_visualization.png', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print("✓ Visualization saved as: benchmark_visualization.png")

# Also save as PDF for academic papers
plt.savefig('benchmark_visualization.pdf', dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print("✓ PDF version saved as: benchmark_visualization.pdf")

plt.show()
