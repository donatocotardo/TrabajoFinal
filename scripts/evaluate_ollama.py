import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from deidentifier.hybrid_detector import detect_phi_hybrid


DATASET_PATH = Path("data/evaluation/evaluation_dataset.jsonl")
OUTPUT_DIR = Path("results/evaluation")
PREDICTIONS_PATH = OUTPUT_DIR / "ollama_predictions.jsonl"
METRICS_PATH = OUTPUT_DIR / "ollama_metrics_by_scenario.csv"


def normalize_text(text: str) -> str:
    """
    Normalizes entity text for comparison.
    This avoids counting small spacing differences as completely different.
    """
    return " ".join(text.strip().lower().split())


def entity_to_key(entity: dict) -> tuple:
    """
    Converts an entity dictionary into a comparable key.
    """
    return (
        normalize_text(entity["text"]),
        entity["label"].strip().upper(),
    )


def load_jsonl(path: Path) -> list[dict]:
    examples = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                examples.append(json.loads(line))

    return examples


def compute_metrics(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    failure_rate = fn / (tp + fn) if (tp + fn) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "failure_rate": failure_rate,
    }


def evaluate_example(example: dict, model: str) -> dict:
    """
    Evaluates a single example:
    - expected entities are taken from the evaluation dataset
    - predicted entities are returned by the local LLM
    """

    text = example["text"]
    expected_entities = example["expected_entities"]

    detection_result = detect_phi_hybrid(text, model=model)

    predicted_entities = [
        {
            "text": entity.text,
            "label": entity.label,
        }
        for entity in detection_result.entities
    ]

    expected_set = {entity_to_key(entity) for entity in expected_entities}
    predicted_set = {entity_to_key(entity) for entity in predicted_entities}

    true_positives = expected_set & predicted_set
    false_positives = predicted_set - expected_set
    false_negatives = expected_set - predicted_set

    metrics = compute_metrics(
        tp=len(true_positives),
        fp=len(false_positives),
        fn=len(false_negatives),
    )

    return {
        "id": example["id"],
        "scenario": example["scenario"],
        "text": text,
        "expected_entities": expected_entities,
        "predicted_entities": predicted_entities,
        "true_positives": [
            {"text": text, "label": label}
            for text, label in sorted(true_positives)
        ],
        "false_positives": [
            {"text": text, "label": label}
            for text, label in sorted(false_positives)
        ],
        "false_negatives": [
            {"text": text, "label": label}
            for text, label in sorted(false_negatives)
        ],
        "tp": len(true_positives),
        "fp": len(false_positives),
        "fn": len(false_negatives),
        **metrics,
    }


def aggregate_by_scenario(results: list[dict]) -> list[dict]:
    """
    Aggregates TP, FP and FN by scenario and computes global metrics
    for each scenario.
    """

    grouped = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "num_examples": 0})

    for result in results:
        scenario = result["scenario"]
        grouped[scenario]["tp"] += result["tp"]
        grouped[scenario]["fp"] += result["fp"]
        grouped[scenario]["fn"] += result["fn"]
        grouped[scenario]["num_examples"] += 1

    rows = []

    for scenario, counts in grouped.items():
        metrics = compute_metrics(
            tp=counts["tp"],
            fp=counts["fp"],
            fn=counts["fn"],
        )

        rows.append(
            {
                "scenario": scenario,
                "num_examples": counts["num_examples"],
                "tp": counts["tp"],
                "fp": counts["fp"],
                "fn": counts["fn"],
                "precision": round(metrics["precision"], 4),
                "recall": round(metrics["recall"], 4),
                "f1": round(metrics["f1"], 4),
                "failure_rate": round(metrics["failure_rate"], 4),
            }
        )

    rows.sort(key=lambda row: row["scenario"])

    return rows


def save_predictions(results: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for result in results:
            file.write(json.dumps(result, ensure_ascii=False) + "\n")


def save_metrics_csv(rows: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario",
        "num_examples",
        "tp",
        "fp",
        "fn",
        "precision",
        "recall",
        "f1",
        "failure_rate",
    ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_metrics_table(rows: list[dict]):
    print("\n===== METRICS BY SCENARIO =====")
    print(
        f"{'Scenario':<28} {'N':>3} {'TP':>4} {'FP':>4} {'FN':>4} "
        f"{'Precision':>10} {'Recall':>8} {'F1':>8} {'Failure':>8}"
    )
    print("-" * 90)

    for row in rows:
        print(
            f"{row['scenario']:<28} "
            f"{row['num_examples']:>3} "
            f"{row['tp']:>4} "
            f"{row['fp']:>4} "
            f"{row['fn']:>4} "
            f"{row['precision']:>10.4f} "
            f"{row['recall']:>8.4f} "
            f"{row['f1']:>8.4f} "
            f"{row['failure_rate']:>8.4f}"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=str,
        default="qwen2.5:7b-instruct",
        help="Ollama model name",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for quick tests",
    )

    args = parser.parse_args()

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_PATH}\n"
            "Run scripts/generate_evaluation_dataset.py first."
        )

    examples = load_jsonl(DATASET_PATH)

    if args.limit is not None:
        examples = examples[: args.limit]

    print(f"Loaded {len(examples)} evaluation examples.")
    print(f"Using Ollama model: {args.model}")

    results = []

    for index, example in enumerate(examples, start=1):
        print(
            f"[{index}/{len(examples)}] "
            f"Evaluating example {example['id']} "
            f"({example['scenario']})..."
        )

        try:
            result = evaluate_example(example, model=args.model)
            results.append(result)
        except Exception as exc:
            print(f"Error evaluating example {example['id']}: {exc}")

    metrics_rows = aggregate_by_scenario(results)

    save_predictions(results, PREDICTIONS_PATH)
    save_metrics_csv(metrics_rows, METRICS_PATH)

    print_metrics_table(metrics_rows)

    print("\nSaved files:")
    print(f"- {PREDICTIONS_PATH}")
    print(f"- {METRICS_PATH}")


if __name__ == "__main__":
    main()