from typing import List, Literal
from pydantic import BaseModel, Field
from ollama import chat
from typing import Any


class PHIEntity(BaseModel):
    text: str = Field(description="Exact text span detected in the clinical note")
    label: Literal["NOMBRE", "DIRECCIÓN", "TELÉFONO", "EMAIL", "FECHA","DNI"]


class PHIExtractionResult(BaseModel):
    entities: List[PHIEntity]


def detect_phi_with_ollama(
    text: str,
    model: str = "qwen2.5:7b-instruct"
) -> PHIExtractionResult:
    """
    Detects protected health information using a local LLM through Ollama.
    The model must return only structured JSON.
    """

    prompt = f"""
You are a clinical text de-identification assistant.

Your task is to detect protected health information in the text.

Detect only the following categories:

- NOMBRE: patient names, doctor names or personal names
- DIRECCIÓN: street addresses, cities with full address, postal addresses
- TELÉFONO: phone numbers
- EMAIL: email addresses
- FECHA: dates, dates of birth, visit dates, admission dates
- DNI: Spanish national identity document numbers, with or without the final letter

Important rules:
- Return only exact text spans that appear in the input.
- Return only the sensitive value, not the field name.
- If the input says "Patient name: John Smith", return only "John Smith".
- If the input says "Patiemt nme: John Smith", return only "John Smith".
- If the input says "Adress: 24 Green Street", return only "24 Green Street".
- If the input says "DNI number: 12345678A", return only "12345678A".
- If the input says "Dr. Pamela Lopez", return only "Pamela Lopez".
- Do not rewrite the medical content.
- Do not invent entities.
- Do not include clinical conditions, diagnoses, symptoms, treatments, medications or diseases.
- Detect identifiers even if the field name contains abbreviations or spelling mistakes.
- If a Spanish DNI appears without being explicitly labelled as DNI, detect it as DNI when it looks like a Spanish ID number.

Clinical text:
{text}
"""

    response = chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        format=PHIExtractionResult.model_json_schema(),
        options={
            "temperature": 0
        }
    )
    try:
        return PHIExtractionResult.model_validate_json(
            response["message"]["content"]
        )
    except Exception as e:  # catch ResponseError or parse errors
        err_text = str(e)
        if "not found" in err_text and "model" in err_text:
            raise RuntimeError(
                f"El modelo '{model}' no se encuentra en Ollama. "
                "Instálalo localmente (p.ej. `ollama pull <model>`), o pasa un modelo existente "
                "como argumento a `detect_phi_with_ollama(model=...)`."
            ) from e
        raise