import csv
import json
from collections import defaultdict
from pathlib import Path


METRICS_PATH = Path("results/evaluation/ollama_metrics_by_scenario.csv")
ENTITY_LABEL_METRICS_PATH = Path("results/evaluation/ollama_metrics_by_label.csv")
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
    lines.append("| Scenario | N | Support | Precision | Recall | F1-score | Miss rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")

    for row in metrics_rows:
        support = row.get("support", "—")
        name = f"**{row['scenario']}**" if row["scenario"] == "TOTAL" else row["scenario"]
        lines.append(
            f"| {name} "
            f"| {row['num_examples']} "
            f"| {support} "
            f"| {format_percentage(row['precision'])} "
            f"| {format_percentage(row['recall'])} "
            f"| {format_percentage(row['f1'])} "
            f"| {format_percentage(row['failure_rate'])} |"
        )

    return "\n".join(lines)


def generate_entity_label_table(label_rows):
    lines = []
    lines.append("| Entity type | Support | Precision | Recall | F1-score | Miss rate |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for row in label_rows:
        support = row.get("support", "—")
        name = f"**{row['label']}**" if row["label"] == "TOTAL" else row["label"]
        lines.append(
            f"| {name} "
            f"| {support} "
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
    scenario_rows = [r for r in metrics_rows if r["scenario"] != "TOTAL"]
    total_row = next((r for r in metrics_rows if r["scenario"] == "TOTAL"), None)

    best_f1 = max(float(r["f1"]) for r in scenario_rows)
    worst_f1 = min(float(r["f1"]) for r in scenario_rows)

    best_scenarios = [r["scenario"] for r in scenario_rows if float(r["f1"]) == best_f1]
    worst_scenarios = [r["scenario"] for r in scenario_rows if float(r["f1"]) == worst_f1]

    lines = []
    lines.append("## Global interpretation")
    lines.append("")

    if total_row:
        total_support = total_row.get("support", "N/A")
        lines.append(
            f"Overall results across **{total_row['num_examples']} examples** "
            f"and **{total_support} expected entities**: "
            f"Precision {format_percentage(total_row['precision'])}, "
            f"Recall {format_percentage(total_row['recall'])}, "
            f"F1-score {format_percentage(total_row['f1'])}."
        )
        lines.append("")

    best_names = ", ".join(f"`{s}`" for s in best_scenarios)
    lines.append(
        f"The best-performing scenario{'s were' if len(best_scenarios) > 1 else ' was'} "
        f"{best_names} with an F1-score of {format_percentage(str(best_f1))}."
    )

    worst_names = ", ".join(f"`{s}`" for s in worst_scenarios)
    lines.append(
        f"The most challenging scenario{'s were' if len(worst_scenarios) > 1 else ' was'} "
        f"{worst_names} with an F1-score of {format_percentage(str(worst_f1))}."
    )

    lines.append("")
    lines.append(
        "These results allow us to identify the conditions under which the local LLM-based "
        "de-identification system is more reliable and the cases where further improvements "
        "would be required."
    )

    return "\n".join(lines)


def main():
    for path, label in [
        (METRICS_PATH, "Metrics file"),
        (PREDICTIONS_PATH, "Predictions file"),
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"{label} not found: {path}\n"
                "Run scripts/evaluate_ollama.py first."
            )

    metrics_rows = load_metrics(METRICS_PATH)
    predictions = load_predictions(PREDICTIONS_PATH)

    label_rows = []
    if ENTITY_LABEL_METRICS_PATH.exists():
        label_rows = load_metrics(ENTITY_LABEL_METRICS_PATH)

    grouped_errors = group_errors_by_scenario(predictions)

    report_parts = [
        "# Evaluation report",
        "",
        "## Metrics by scenario",
        "",
        generate_metrics_table(metrics_rows),
        "",
        generate_global_summary(metrics_rows),
    ]

    if label_rows:
        report_parts += [
            "",
            "## Metrics by entity type",
            "",
            generate_entity_label_table(label_rows),
        ]

    report_parts += [
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