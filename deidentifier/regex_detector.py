import re
from typing import List

from deidentifier.llm_detector import PHIEntity


def _normalize_key(text: str, label: str) -> tuple:
    return (" ".join(text.lower().strip().split()), label.upper())


def _clean_value(value: str) -> str:
    value = value.strip()
    value = value.strip(" \t\n\r\"'`")
    value = re.sub(r"\s+", " ", value)
    value = value.rstrip(".,;")
    return value


def _add_entity(entities: List[PHIEntity], value: str, label: str):
    value = _clean_value(value)

    if value:
        entities.append(PHIEntity(text=value, label=label))


def detect_phi_with_regex(text: str) -> List[PHIEntity]:
    """
    Detects structured PHI using deterministic regular expressions.

    This layer is not intended to replace the local LLM.
    It supports the LLM in structured cases:
    - emails
    - dates
    - phone numbers
    - Spanish DNI
    - field-based values, including abbreviations and common typos
    """

    entities: List[PHIEntity] = []

    field_patterns = [
        (
            "NOMBRE",
            r"(?im)^\s*(?:patient\s+name|name|patient|pt|patiemt\s+nme|patiemt\s+name)\s*:\s*(?P<value>.+?)\s*$",
        ),
        (
            "FECHA",
            r"(?im)^\s*(?:date\s+of\s+birth|dob|dtae\s+of\s+brith|visit\s+date)\s*:\s*(?P<value>.+?)\s*$",
        ),
        (
            "DIRECCIÓN",
            r"(?im)^\s*(?:address|addr|adress)\s*:\s*(?P<value>.+?)\s*$",
        ),
        (
            "TELÉFONO",
            r"(?im)^\s*(?:phone|telephone|tel|phne|phone\s+number)\s*:\s*(?P<value>.+?)\s*$",
        ),
        (
            "EMAIL",
            r"(?im)^\s*(?:email|mail|emial|email\s+address)\s*:\s*(?P<value>.+?)\s*$",
        ),
        (
            "DNI",
            r"(?im)^\s*(?:dni\s+number|dni|id|identification\s+number|additional\s+numeric\s+identifier|numeric\s+identifier)\s*:\s*(?P<value>\d{8}[A-Za-z]?)\s*$",
        ),
    ]

    for label, pattern in field_patterns:
        for match in re.finditer(pattern, text):
            _add_entity(entities, match.group("value"), label)

    # Generic email detection
    for match in re.finditer(
        r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b",
        text,
    ):
        _add_entity(entities, match.group(0), "EMAIL")

    # Generic date detection
    # Examples: 03/12/1985, 3-12-85, 2024-05-21
    for match in re.finditer(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
        text,
    ):
        _add_entity(entities, match.group(0), "FECHA")

    # Generic phone detection.
    # It requires separators or an extension, so plain 8-digit DNI numbers are not wrongly classified as phones.
    for match in re.finditer(
        r"(?<!\w)(?:\+?\d{1,3}[\s.-])?(?:\(?\d{2,4}\)?[\s.-]){1,3}\d{2,4}(?:x\d{1,6})?(?!\w)",
        text,
    ):
        _add_entity(entities, match.group(0), "TELÉFONO")

    # Spanish DNI with final letter
    for match in re.finditer(
        r"(?<!\w)\d{8}[A-Za-z](?!\w)",
        text,
    ):
        _add_entity(entities, match.group(0), "DNI")

    # Spanish DNI without final letter, only when context suggests an ID.
    for match in re.finditer(
        r"(?i)\b(?:dni\s+number|dni|id|identification\s+number|numeric\s+identifier)\s*:\s*(\d{8})\b",
        text,
    ):
        _add_entity(entities, match.group(1), "DNI")

    # Doctor names in long mixed reports.
    # Example: Dr. Pamela Lopez
    for match in re.finditer(
        r"\bDr\.?\s+([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){1,3})\b",
        text,
    ):
        _add_entity(entities, match.group(1), "NOMBRE")

    # Unlabelled name at the beginning of a sentence.
    # Example: John Smith came to the clinic today.
    for match in re.finditer(
        r"(?m)^\s*([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){1,3})\s+came\s+to\s+the\s+clinic\s+today\.?",
        text,
    ):
        _add_entity(entities, match.group(1), "NOMBRE")

    # Remove duplicates
    unique_entities = []
    seen = set()

    for entity in entities:
        key = _normalize_key(entity.text, entity.label)
        if key not in seen:
            unique_entities.append(entity)
            seen.add(key)

    return unique_entities