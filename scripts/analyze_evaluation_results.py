import csv
import json
from collections import defaultdict
from pathlib import Path


METRICS_PATH = Path("results/evaluation/ollama_metrics_by_scenario.csv")
PREDICTIONS_PATH = Path("results/evaluation/ollama_predictions.jsonl")
REPORT_PATH = Path("results/evaluation/evaluation_report.md")


def load_metrics(path: Path):
    with path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def load_predictions(path: Path):
    predictions = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                predictions.append(json.loads(line))

    return predictions


def format_percentage(value):
    return f"{float(value) * 100:.2f}%"


def generate_metrics_table(metrics_rows):
    lines = []
    lines.append("| Scenario | Examples | Precision | Recall | F1-score | Failure rate |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for row in metrics_rows:
        lines.append(
            f"| {row['scenario']} "
            f"| {row['num_examples']} "
            f"| {format_percentage(row['precision'])} "
            f"| {format_percentage(row['recall'])} "
            f"| {format_percentage(row['f1'])} "
            f"| {format_percentage(row['failure_rate'])} |"
        )

    return "\n".join(lines)


def group_errors_by_scenario(predictions):
    grouped = defaultdict(lambda: {"false_positives": [], "false_negatives": []})

    for prediction in predictions:
        scenario = prediction["scenario"]

        for fp in prediction.get("false_positives", []):
            grouped[scenario]["false_positives"].append(fp)

        for fn in prediction.get("false_negatives", []):
            grouped[scenario]["false_negatives"].append(fn)

    return grouped


def summarize_errors(grouped_errors):
    lines = []

    for scenario, errors in grouped_errors.items():
        false_positives = errors["false_positives"]
        false_negatives = errors["false_negatives"]

        lines.append(f"## Scenario: {scenario}")
        lines.append("")

        lines.append(f"- False positives: {len(false_positives)}")
        lines.append(f"- False negatives: {len(false_negatives)}")
        lines.append("")

        if false_positives:
            lines.append("### Examples of false positives")
            for entity in false_positives[:5]:
                lines.append(f"- `{entity['text']}` classified as `{entity['label']}`")
            lines.append("")

        if false_negatives:
            lines.append("### Examples of false negatives")
            for entity in false_negatives[:5]:
                lines.append(f"- `{entity['text']}` expected as `{entity['label']}`")
            lines.append("")

        if not false_positives and not false_negatives:
            lines.append("No errors detected in this scenario.")
            lines.append("")

    return "\n".join(lines)


def generate_global_summary(metrics_rows):
    best = max(metrics_rows, key=lambda row: float(row["f1"]))
    worst = min(metrics_rows, key=lambda row: float(row["f1"]))

    lines = []

    lines.append("## Global interpretation")
    lines.append("")
    lines.append(
        f"The best-performing scenario was `{best['scenario']}` "
        f"with an F1-score of {format_percentage(best['f1'])}."
    )
    lines.append(
        f"The most challenging scenario was `{worst['scenario']}` "
        f"with an F1-score of {format_percentage(worst['f1'])}."
    )
    lines.append("")
    lines.append(
        "These results allow us to identify the conditions under which the local LLM-based "
        "de-identification system is more reliable and the cases where further improvements "
        "would be required."
    )

    return "\n".join(lines)


def main():
    if not METRICS_PATH.exists():
        raise FileNotFoundError(
            f"Metrics file not found: {METRICS_PATH}\n"
            "Run scripts/evaluate_ollama.py first."
        )

    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Predictions file not found: {PREDICTIONS_PATH}\n"
            "Run scripts/evaluate_ollama.py first."
        )

    metrics_rows = load_metrics(METRICS_PATH)
    predictions = load_predictions(PREDICTIONS_PATH)

    grouped_errors = group_errors_by_scenario(predictions)

    report_parts = [
        "# Evaluation report",
        "",
        "## Metrics by scenario",
        "",
        generate_metrics_table(metrics_rows),
        "",
        generate_global_summary(metrics_rows),
        "",
        "# Error analysis",
        "",
        summarize_errors(grouped_errors),
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        file.write("\n".join(report_parts))

    print(f"Evaluation report generated at: {REPORT_PATH}")


if __name__ == "__main__":
    main()