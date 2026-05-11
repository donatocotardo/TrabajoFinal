from deidentifier.llm_detector import detect_phi_with_ollama


def replace_entities_with_labels(text: str, entities) -> str:
    """
    Replaces detected PHI entities with their corresponding labels.

    The replacement is done carefully:
    - longer entities are replaced first
    - duplicated entities are avoided
    - the rest of the clinical text remains unchanged
    """

    anonymized_text = text

    # Remove duplicated entities
    unique_entities = []
    seen = set()

    for entity in entities:
        key = (entity.text, entity.label)
        if key not in seen:
            unique_entities.append(entity)
            seen.add(key)

    # Replace longer spans first to avoid partial replacements
    unique_entities = sorted(
        unique_entities,
        key=lambda e: len(e.text),
        reverse=True
    )

    for entity in unique_entities:
        label = f"[{entity.label}]"
        anonymized_text = anonymized_text.replace(entity.text, label)

    return anonymized_text


def anonymize_text_with_ollama(
    text: str,
    model: str = "qwen2.5:7b-instruct"
) -> str:
    """
    Full anonymization pipeline:
    1. Detect PHI entities using a local LLM.
    2. Replace those entities with predefined labels.
    """

    detection_result = detect_phi_with_ollama(text, model=model)

    anonymized_text = replace_entities_with_labels(
        text,
        detection_result.entities
    )

    return anonymized_text