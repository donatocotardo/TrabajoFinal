from faker import Faker
import json
import random
from pathlib import Path


fake = Faker("en_US")

OUTPUT_PATH = Path("data/synthetic/synthetic_phi_examples.jsonl")


CLINICAL_TEMPLATES = [
    "The patient presents with abdominal pain, nausea and mild fever. Past medical history includes Crohn's disease.",
    "The patient reports persistent headache and dizziness. Neurological examination was normal.",
    "The patient was admitted due to chest pain and shortness of breath. ECG and blood tests were requested.",
    "The patient presents with cough, sore throat and general fatigue. Symptomatic treatment was recommended.",
    "The patient has a history of hypertension and type 2 diabetes. Medication adherence was discussed.",
    "The patient reports lower back pain after physical effort. No neurological deficits were observed.",
    "The patient presents with skin rash and itching. An allergic reaction was suspected.",
    "The patient attended a follow-up visit after surgery. Wound healing was satisfactory.",
]


def generate_example(example_id: int) -> dict:
    """
    Generates one synthetic clinical text containing fake protected health information.
    The returned dictionary includes both the original text and the expected PHI labels.
    """

    name = fake.name()
    address = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()
    date_of_birth = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
    visit_date = fake.date_between(start_date="-3y", end_date="today").strftime("%m/%d/%Y")

    clinical_note = random.choice(CLINICAL_TEMPLATES)

    original_text = f"""Patient name: {name}
Date of birth: {date_of_birth}
Address: {address}
Phone: {phone}
Email: {email}
Visit date: {visit_date}

Clinical note:
{clinical_note}
"""

    anonymized_text = f"""Patient name: [NOMBRE]
Date of birth: [FECHA]
Address: [DIRECCIÓN]
Phone: [TELÉFONO]
Email: [EMAIL]
Visit date: [FECHA]

Clinical note:
{clinical_note}
"""

    entities = [
        {"text": name, "label": "NOMBRE"},
        {"text": date_of_birth, "label": "FECHA"},
        {"text": address, "label": "DIRECCIÓN"},
        {"text": phone, "label": "TELÉFONO"},
        {"text": email, "label": "EMAIL"},
        {"text": visit_date, "label": "FECHA"},
    ]

    return {
        "id": example_id,
        "original_text": original_text,
        "anonymized_text": anonymized_text,
        "entities": entities,
    }


def generate_dataset(num_examples: int = 100):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        for i in range(num_examples):
            example = generate_example(i)
            file.write(json.dumps(example, ensure_ascii=False) + "\n")

    print(f"Generated {num_examples} synthetic examples.")
    print(f"Saved at: {OUTPUT_PATH}")


if __name__ == "__main__":
    generate_dataset(num_examples=100)