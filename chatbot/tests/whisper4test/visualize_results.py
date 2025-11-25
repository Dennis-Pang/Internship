#!/usr/bin/env python3
"""
Whisper Benchmark可视化工具
按模型分组展示不同配置的准确率和时间对比(忽略batch size差异)
"""

import re
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

def parse_summary_file(filepath):
    """解析summary.md文件"""
    data = []

    with open(filepath, 'r') as f:
        for line in f:
            # 跳过标题行
            if line.startswith('=') or line.startswith('Model') or line.startswith('-'):
                continue

            parts = line.strip().split()
            if len(parts) >= 5:
                model = parts[0]
                config = parts[1]
                difficulty = parts[2]
                time_str = parts[3]
                accuracy_str = parts[4]

                # 提取数值
                time_val = float(time_str.rstrip('s'))
                accuracy_val = float(accuracy_str.rstrip('%'))

                data.append({
                    'model': model,
                    'config': config,
                    'difficulty': difficulty,
                    'time': time_val,
                    'accuracy': accuracy_val
                })

    return data

def aggregate_by_config(data):
    """
    按模型和配置聚合数据(忽略batch size)
    计算所有难度和batch size的平均准确率和时间
    """
    grouped = defaultdict(lambda: {'time': [], 'accuracy': []})

    for item in data:
        model = item['model'].split('/')[-1]  # 简化模型名
        config = item['config']

        # 提取基础配置(去掉batch size)
        match = re.match(r'(fp\d+)_batch\d+_(flash|sdpa)', config)
        if match:
            precision = match.group(1)
            attention = match.group(2)
            config_base = f"{precision}_{attention}"
        else:
            config_base = config

        key = (model, config_base)
        grouped[key]['time'].append(item['time'])
        grouped[key]['accuracy'].append(item['accuracy'])

    # 计算平均值
    aggregated = []
    for (model, config_base), values in grouped.items():
        avg_time = np.mean(values['time'])
        avg_accuracy = np.mean(values['accuracy'])
        aggregated.append({
            'model': model,
            'config': config_base,
            'avg_time': avg_time,
            'avg_accuracy': avg_accuracy
        })

    return aggregated

def create_grouped_chart(aggregated_data, output_path='benchmark_visualization.png'):
    """创建组装柱状图"""
    # 提取唯一的模型和配置
    models = []
    model_order = ['whisper-tiny', 'whisper-base', 'whisper-small',
                   'whisper-medium', 'whisper-large-v3-turbo', 'whisper-large-v3']

    for m in model_order:
        if any(item['model'] == m for item in aggregated_data):
            models.append(m)

    configs = sorted(set(item['config'] for item in aggregated_data))

    # 组织数据
    data_dict = {model: {config: {'time': 0, 'accuracy': 0} for config in configs}
                 for model in models}

    for item in aggregated_data:
        if item['model'] in models:
            data_dict[item['model']][item['config']]['time'] = item['avg_time']
            data_dict[item['model']][item['config']]['accuracy'] = item['avg_accuracy']

    # 设置图形
    fig, axes = plt.subplots(2, 1, figsize=(18, 12))

    # 定义颜色
    colors = {
        'fp16_flash': '#2ecc71',
        'fp16_sdpa': '#3498db',
        'fp32_sdpa': '#e74c3c'
    }

    bar_width = 0.25
    x = np.arange(len(models))

    # 图1: 准确率对比
    ax1 = axes[0]
    for i, config in enumerate(configs):
        accuracies = [data_dict[model][config]['accuracy'] for model in models]
        offset = (i - len(configs)/2 + 0.5) * bar_width
        ax1.bar(x + offset, accuracies, bar_width,
               label=config, color=colors.get(config, '#95a5a6'), alpha=0.85)

        # 在柱子上添加数值
        for j, acc in enumerate(accuracies):
            if acc > 0:
                ax1.text(j + offset, acc + 1, f'{acc:.1f}%',
                        ha='center', va='bottom', fontsize=10, rotation=0)

    ax1.set_xlabel('Model', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Average Accuracy (%)', fontsize=16, fontweight='bold')
    ax1.set_title('Accuracy Comparison',
                 fontsize=20, fontweight='bold', pad=20)
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=30, ha='right', fontsize=13)
    ax1.set_ylim([0, 110])
    ax1.legend(title='Configuration', fontsize=13, title_fontsize=14, loc='lower right')
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # 图2: 时间对比
    ax2 = axes[1]
    for i, config in enumerate(configs):
        times = [data_dict[model][config]['time'] for model in models]
        offset = (i - len(configs)/2 + 0.5) * bar_width
        ax2.bar(x + offset, times, bar_width,
               label=config, color=colors.get(config, '#95a5a6'), alpha=0.85)

        # 在柱子上添加数值
        for j, time_val in enumerate(times):
            if time_val > 0:
                ax2.text(j + offset, time_val + max(times)*0.02, f'{time_val:.1f}s',
                        ha='center', va='bottom', fontsize=10, rotation=0)

    ax2.set_xlabel('Model', fontsize=16, fontweight='bold')
    ax2.set_ylabel('Average Processing Time (seconds)', fontsize=16, fontweight='bold')
    ax2.set_title('Processing Time Comparison',
                 fontsize=20, fontweight='bold', pad=20)
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, rotation=30, ha='right', fontsize=13)
    ax2.legend(title='Configuration', fontsize=13, title_fontsize=14, loc='upper left')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()

    # 保存图片
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Chart saved: {output_path}")

    # 同时保存PDF版本
    pdf_path = output_path.replace('.png', '.pdf')
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    plt.show()

def print_recommendations(aggregated_data):
    """输出推荐配置"""
    print("\n" + "="*80)
    print("RECOMMENDED CONFIGURATIONS")
    print("="*80)

    # 按准确率排序
    sorted_by_acc = sorted(aggregated_data,
                          key=lambda x: (-x['avg_accuracy'], x['avg_time']))

    print("\nTop 5 by Accuracy (accuracy↓, time↑):")
    print(f"{'Rank':<6}{'Model':<30}{'Config':<18}{'Accuracy':<12}{'Time'}")
    print("-"*80)
    for i, item in enumerate(sorted_by_acc[:5], 1):
        print(f"{i:<6}{item['model']:<30}{item['config']:<18}"
              f"{item['avg_accuracy']:>10.2f}%  {item['avg_time']:>10.2f}s")

    # 按速度排序(只看高准确率的)
    high_acc = [x for x in aggregated_data if x['avg_accuracy'] > 90]
    sorted_by_speed = sorted(high_acc, key=lambda x: x['avg_time'])

    print("\nTop 5 by Speed (accuracy>90%):")
    print(f"{'Rank':<6}{'Model':<30}{'Config':<18}{'Accuracy':<12}{'Time'}")
    print("-"*80)
    for i, item in enumerate(sorted_by_speed[:5], 1):
        print(f"{i:<6}{item['model']:<30}{item['config']:<18}"
              f"{item['avg_accuracy']:>10.2f}%  {item['avg_time']:>10.2f}s")

    # 效率分数(准确率/时间)
    for item in aggregated_data:
        item['efficiency'] = item['avg_accuracy'] / item['avg_time']

    sorted_by_eff = sorted(aggregated_data, key=lambda x: -x['efficiency'])

    print("\nTop 5 by Overall Efficiency (accuracy/time):")
    print(f"{'Rank':<6}{'Model':<30}{'Config':<18}{'Efficiency':<14}{'Accuracy':<12}{'Time'}")
    print("-"*80)
    for i, item in enumerate(sorted_by_eff[:5], 1):
        print(f"{i:<6}{item['model']:<30}{item['config']:<18}"
              f"{item['efficiency']:>12.2f}  {item['avg_accuracy']:>10.2f}%  {item['avg_time']:>10.2f}s")

    print("\n" + "="*80)
    print("RECOMMENDATION:")
    best = sorted_by_eff[0]
    print(f"   Best configuration: {best['model']} + {best['config']}")
    print(f"   - Accuracy: {best['avg_accuracy']:.2f}%")
    print(f"   - Processing time: {best['avg_time']:.2f}s")
    print(f"   - Efficiency score: {best['efficiency']:.2f} (accuracy%/second)")
    print("="*80 + "\n")

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 确定summary.md路径
    if len(sys.argv) > 1:
        summary_path = sys.argv[1]
    else:
        # 默认路径
        summary_path = Path(__file__).parent / 'summary.md'

    print("="*80)
    print("Whisper Performance Visualization Tool")
    print("="*80)
    print(f"Data source: {summary_path}\n")

    # 解析数据
    print("Parsing data...")
    data = parse_summary_file(summary_path)
    print(f"✓ Loaded {len(data)} data points\n")

    # 聚合数据
    print("Aggregating data (ignoring batch size)...")
    aggregated = aggregate_by_config(data)
    print(f"✓ Aggregated into {len(aggregated)} model-config combinations\n")

    # 生成图表
    print("Generating visualization...")
    output_path = Path(__file__).parent / 'benchmark_visualization.png'
    create_grouped_chart(aggregated, str(output_path))

    # 输出推荐
    print_recommendations(aggregated)
