#!/usr/bin/env python3
"""Create bar charts for the whisper speech2text benchmark results."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

MODEL_ORDER = [
    "openai/whisper-tiny",
    "openai/whisper-small",
    "openai/whisper-medium",
    "openai/whisper-base",
    "openai/whisper-large-v3-turbo",
    "openai/whisper-large-v3",
]
CONFIG_ORDER = ["FP16 • FLASH", "FP16 • SDPA", "FP32 • SDPA"]
CONFIG_COLORS = {
    "FP16 • FLASH": "#80b1d3",
    "FP16 • SDPA": "#4daf4a",
    "FP32 • SDPA": "#984ea3",
}


def load_data(data_path: Path) -> pd.DataFrame:
    """Load and enrich the aggregated benchmark table."""
    df = pd.read_csv(data_path, sep="\t")
    df["Precision"] = df["Config"].str.extract(r"(fp\d+)")
    df["Batch"] = df["Config"].str.extract(r"batch(\d+)").astype(int)
    df["Attention"] = df["Config"].str.extract(r"(flash|sdpa)")
    return df


def summarize_configs(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics by precision + attention to keep the bars readable."""
    summary = (
        df.groupby(["Model", "Precision", "Attention"], as_index=False)
        .agg(
            {
                "Avg Time (s)": "mean",
                "Avg Accuracy (%)": "mean",
                "Avg Word Errs": "mean",
            }
        )
    )
    summary["Config Label"] = summary["Precision"].str.upper() + " • " + summary["Attention"].str.upper()
    summary["Model"] = pd.Categorical(summary["Model"], categories=MODEL_ORDER, ordered=True)
    summary = summary[summary["Config Label"].isin(CONFIG_ORDER)]
    summary = summary.sort_values("Model")
    return summary


def build_plot(summary: pd.DataFrame, output_path: Path) -> None:
    """Render three aligned horizontal bar charts."""
    sns.set_theme(style="whitegrid")

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharey=True)
    metric_specs = [
        ("Avg Time (s)", "Average Time (s)", "Latency per model", "{:.1f}s"),
        ("Avg Accuracy (%)", "Average Accuracy (%)", "Accuracy per model", "{:.2f}%"),
        ("Avg Word Errs", "Average Word Errors", "Word errors per model", "{:.1f}"),
    ]

    palette = [CONFIG_COLORS[label] for label in CONFIG_ORDER]

    for ax, (column, xlabel, title, fmt) in zip(axes, metric_specs):
        sns.barplot(
            data=summary,
            x=column,
            y="Model",
            hue="Config Label",
            order=MODEL_ORDER,
            hue_order=CONFIG_ORDER,
            palette=palette,
            ax=ax,
            orient="h",
            errorbar=None,
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel("")
        ax.set_title(title, loc="left")

        max_width = summary[column].max()
        for bar in ax.patches:
            width = bar.get_width()
            if pd.isna(width) or width == 0:
                continue
            ax.text(
                width + max_width * 0.01,
                bar.get_y() + bar.get_height() / 2,
                fmt.format(width),
                va="center",
                fontsize=9,
                color="#333333",
            )

    axes[0].legend(loc="lower right", title="Precision • Attention")
    axes[1].get_legend().remove()
    axes[2].get_legend().remove()

    fig.suptitle("Whisper Speech2Text Benchmark Overview (Bar Charts)", fontsize=16, weight="bold")
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    data_path = base_dir / "avg.txt"
    output_path = base_dir / "whisper_config_tradeoffs.png"
    df = load_data(data_path)
    summary = summarize_configs(df)
    build_plot(summary, output_path)
    rel_path = output_path.relative_to(base_dir)
    print(f"Saved visualization to {output_path} ({rel_path}).")


if __name__ == "__main__":
    main()
