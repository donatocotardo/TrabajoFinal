import re
from typing import List, Optional

from deidentifier.llm_detector import (
    PHIEntity,
    PHIExtractionResult,
    detect_phi_with_ollama,
)
from deidentifier.regex_detector import detect_phi_with_regex


def _normalize_key(text: str, label: str) -> tuple:
    return (" ".join(text.lower().strip().split()), label.upper())


def _find_case_preserved_span(span: str, original_text: str) -> str:
    """
    If the LLM returns a lowercased span, this function tries to recover
    the original casing from the input text.
    """

    if span in original_text:
        return span

    match = re.search(re.escape(span), original_text, flags=re.IGNORECASE)

    if match:
        return match.group(0)

    return span


def clean_llm_entity(entity: PHIEntity, original_text: str) -> Optional[PHIEntity]:
    """
    Cleans common LLM mistakes.

    Example:
    - 'Patiemt nme: Jennifer Santiago' -> 'Jennifer Santiago'
    - 'Adress: 24 Green Street' -> '24 Green Street'
    - 'Dr. Pamela Lopez' -> 'Pamela Lopez'
    """

    span = entity.text.strip()
    span = span.strip(" \t\n\r\"'`")

    # If the model included the field name, keep only the value after the colon.
    if ":" in span:
        possible_value = span.split(":", 1)[1].strip()
        if possible_value:
            span = possible_value

    # For doctor names, keep only the personal name.
    if entity.label == "NOMBRE":
        span = re.sub(r"(?i)^dr\.?\s+", "", span).strip()

    span = span.rstrip(".,;")
    span = re.sub(r"\s+", " ", span)

    if not span:
        return None

    span = _find_case_preserved_span(span, original_text)

    return PHIEntity(text=span, label=entity.label)


def merge_entities(entities: List[PHIEntity]) -> List[PHIEntity]:
    """
    Removes duplicate entities while preserving the first occurrence.
    """

    unique_entities = []
    seen = set()

    for entity in entities:
        entity_text = entity.text.strip()

        if not entity_text:
            continue

        key = _normalize_key(entity_text, entity.label)

        if key not in seen:
            unique_entities.append(PHIEntity(text=entity_text, label=entity.label))
            seen.add(key)

    return unique_entities


def detect_phi_hybrid(
    text: str,
    model: str = "qwen2.5:7b-instruct",
) -> PHIExtractionResult:
    """
    Final PHI detection pipeline.

    It combines:
    1. Local LLM detection through Ollama.
    2. Post-processing of LLM spans.
    3. Regex support for structured identifiers.

    The LLM is still local. No external API is used.
    """

    all_entities: List[PHIEntity] = []

    # 1. Local LLM detection
    llm_result = detect_phi_with_ollama(text, model=model)

    for entity in llm_result.entities:
        cleaned_entity = clean_llm_entity(entity, original_text=text)

        if cleaned_entity is not None:
            all_entities.append(cleaned_entity)

    # 2. Regex support layer
    regex_entities = detect_phi_with_regex(text)
    all_entities.extend(regex_entities)

    # 3. Deduplicate
    merged_entities = merge_entities(all_entities)

    return PHIExtractionResult(entities=merged_entities)