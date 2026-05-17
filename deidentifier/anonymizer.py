import re

from deidentifier.hybrid_detector import detect_phi_hybrid


def replace_entities_with_labels(text: str, entities) -> str:
    """
    Replaces detected PHI entities with their corresponding labels.

    Longer entities are replaced first to avoid partial replacements.
    Case-insensitive replacement is used as fallback because some LLMs
    may return lowercased spans.
    """

    anonymized_text = text

    unique_entities = []
    seen = set()

    for entity in entities:
        key = (" ".join(entity.text.lower().strip().split()), entity.label)

        if key not in seen:
            unique_entities.append(entity)
            seen.add(key)

    unique_entities = sorted(
        unique_entities,
        key=lambda e: len(e.text),
        reverse=True,
    )

    for entity in unique_entities:
        label = f"[{entity.label}]"
        span = entity.text.strip()

        if not span:
            continue

        # Exact replacement first
        if span in anonymized_text:
            anonymized_text = anonymized_text.replace(span, label)
        else:
            # Case-insensitive fallback
            anonymized_text = re.sub(
                re.escape(span),
                label,
                anonymized_text,
                flags=re.IGNORECASE,
            )

    return anonymized_text


def anonymize_text_with_ollama(
    text: str,
    model: str = "qwen2.5:7b-instruct",
) -> str:
    """
    Full anonymization pipeline:
    1. Detect PHI using local Ollama + deterministic support rules.
    2. Replace detected PHI with predefined labels.
    """

    detection_result = detect_phi_hybrid(text, model=model)

    anonymized_text = replace_entities_with_labels(
        text,
        detection_result.entities,
    )

    return anonymized_text