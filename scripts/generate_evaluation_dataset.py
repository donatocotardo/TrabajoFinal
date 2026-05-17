import json
import random
from pathlib import Path
from faker import Faker


fake = Faker("en_US")
random.seed(42)
Faker.seed(42)

OUTPUT_PATH = Path("data/evaluation/evaluation_dataset.jsonl")


CLINICAL_NOTES = [
    "The patient presents with abdominal pain, nausea and mild fever. Past medical history includes Crohn's disease.",
    "The patient reports persistent headache and dizziness. Neurological examination was normal.",
    "The patient was admitted due to chest pain and shortness of breath. ECG and blood tests were requested.",
    "The patient has a history of hypertension and type 2 diabetes. Medication adherence was discussed.",
    "The patient presents with cough, sore throat and general fatigue. Symptomatic treatment was recommended.",
]


def save_jsonl(examples, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for example in examples:
            file.write(json.dumps(example, ensure_ascii=False) + "\n")

    print(f"Generated {len(examples)} evaluation examples.")
    print(f"Saved at: {output_path}")


def make_entity(text, label):
    return {
        "text": text,
        "label": label
    }


def generate_standard_case(example_id: int):
    name = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
    address = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()
    visit_date = fake.date_between(start_date="-2y", end_date="today").strftime("%m/%d/%Y")
    dni = "12345678A"

    clinical_note = random.choice(CLINICAL_NOTES)

    text = f"""Patient name: {name}
Date of birth: {dob}
Address: {address}
Phone: {phone}
Email: {email}
Visit date: {visit_date}
DNI: {dni}

Clinical note:
{clinical_note}
"""

    entities = [
        make_entity(name, "NOMBRE"),
        make_entity(dob, "FECHA"),
        make_entity(address, "DIRECCIÓN"),
        make_entity(phone, "TELÉFONO"),
        make_entity(email, "EMAIL"),
        make_entity(visit_date, "FECHA"),
        make_entity(dni, "DNI"),
    ]

    return {
        "id": example_id,
        "scenario": "standard",
        "text": text,
        "expected_entities": entities,
        "sensitive_clinical_terms": [
            "abdominal pain",
            "Crohn's disease",
            "hypertension",
            "type 2 diabetes",
            "corticosteroids"
        ]
    }


def generate_abbreviation_case(example_id: int):
    name = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
    address = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()
    dni = "87654321B"

    clinical_note = random.choice(CLINICAL_NOTES)

    text = f"""Pt: {name}
DOB: {dob}
Addr: {address}
Tel: {phone}
Mail: {email}
ID: {dni}

Clinical note:
{clinical_note}
"""

    entities = [
        make_entity(name, "NOMBRE"),
        make_entity(dob, "FECHA"),
        make_entity(address, "DIRECCIÓN"),
        make_entity(phone, "TELÉFONO"),
        make_entity(email, "EMAIL"),
        make_entity(dni, "DNI"),
    ]

    return {
        "id": example_id,
        "scenario": "abbreviations",
        "text": text,
        "expected_entities": entities,
        "sensitive_clinical_terms": [
            "abdominal pain",
            "Crohn's disease",
            "headache",
            "dizziness"
        ]
    }


def generate_typo_case(example_id: int):
    name = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
    address = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()
    dni = "11223344C"

    clinical_note = random.choice(CLINICAL_NOTES)

    text = f"""Patiemt nme: {name}
Dtae of brith: {dob}
Adress: {address}
Phne: {phone}
Emial: {email}
DNI number: {dni}

Clinical note:
{clinical_note}
"""

    entities = [
        make_entity(name, "NOMBRE"),
        make_entity(dob, "FECHA"),
        make_entity(address, "DIRECCIÓN"),
        make_entity(phone, "TELÉFONO"),
        make_entity(email, "EMAIL"),
        make_entity(dni, "DNI"),
    ]

    return {
        "id": example_id,
        "scenario": "typos",
        "text": text,
        "expected_entities": entities,
        "sensitive_clinical_terms": [
            "chest pain",
            "shortness of breath",
            "hypertension"
        ]
    }


def generate_dni_missing_letter_case(example_id: int):
    name = fake.name()
    dni_without_letter = "45678912"
    clinical_note = random.choice(CLINICAL_NOTES)

    text = f"""Patient: {name}
Identification number: {dni_without_letter}

Clinical note:
{clinical_note}
"""

    entities = [
        make_entity(name, "NOMBRE"),
        make_entity(dni_without_letter, "DNI"),
    ]

    return {
        "id": example_id,
        "scenario": "dni_missing_letter",
        "text": text,
        "expected_entities": entities,
        "sensitive_clinical_terms": [
            "Crohn's disease",
            "abdominal pain",
            "type 2 diabetes"
        ]
    }


def generate_unlabelled_identifier_case(example_id: int):
    name = fake.name()
    phone = fake.phone_number()
    email = fake.email()
    dni = "99887766D"

    clinical_note = random.choice(CLINICAL_NOTES)

    text = f"""{name} came to the clinic today.
Contact information: {phone}, {email}.
Additional numeric identifier: {dni}.

Clinical note:
{clinical_note}
"""

    entities = [
        make_entity(name, "NOMBRE"),
        make_entity(phone, "TELÉFONO"),
        make_entity(email, "EMAIL"),
        make_entity(dni, "DNI"),
    ]

    return {
        "id": example_id,
        "scenario": "unlabelled_identifiers",
        "text": text,
        "expected_entities": entities,
        "sensitive_clinical_terms": [
            "cough",
            "sore throat",
            "fatigue"
        ]
    }


def generate_sensitive_clinical_data_case(example_id: int):
    name = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")

    text = f"""Patient name: {name}
Date of birth: {dob}

Clinical note:
The patient has Crohn's disease, hypertension and type 2 diabetes.
The patient reports abdominal pain and nausea.
Treatment with corticosteroids was discussed.
"""

    entities = [
        make_entity(name, "NOMBRE"),
        make_entity(dob, "FECHA"),
    ]

    return {
        "id": example_id,
        "scenario": "sensitive_clinical_data",
        "text": text,
        "expected_entities": entities,
        "sensitive_clinical_terms": [
            "Crohn's disease",
            "hypertension",
            "type 2 diabetes",
            "abdominal pain",
            "nausea",
            "corticosteroids"
        ]
    }


def generate_long_mixed_text_case(example_id: int):
    name = fake.name()
    doctor = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
    address = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()
    visit_date = fake.date_between(start_date="-2y", end_date="today").strftime("%m/%d/%Y")
    dni = "13572468E"

    text = f"""Clinical consultation report

Patient name: {name}
DOB: {dob}
Address: {address}
Phone number: {phone}
Email address: {email}
DNI: {dni}

The patient was evaluated by Dr. {doctor} on {visit_date}.
The patient reports abdominal pain, nausea and fatigue.
Past medical history includes Crohn's disease and hypertension.
Blood tests and abdominal imaging were requested.
A follow-up visit was recommended if symptoms persist.

End of report.
"""

    entities = [
        make_entity(name, "NOMBRE"),
        make_entity(dob, "FECHA"),
        make_entity(address, "DIRECCIÓN"),
        make_entity(phone, "TELÉFONO"),
        make_entity(email, "EMAIL"),
        make_entity(dni, "DNI"),
        make_entity(doctor, "NOMBRE"),
        make_entity(visit_date, "FECHA"),
    ]

    return {
        "id": example_id,
        "scenario": "long_mixed_text",
        "text": text,
        "expected_entities": entities,
        "sensitive_clinical_terms": [
            "abdominal pain",
            "nausea",
            "fatigue",
            "Crohn's disease",
            "hypertension"
        ]
    }


def generate_evaluation_dataset():
    examples = []
    example_id = 0

    scenario_generators = [
        generate_standard_case,
        generate_abbreviation_case,
        generate_typo_case,
        generate_dni_missing_letter_case,
        generate_unlabelled_identifier_case,
        generate_sensitive_clinical_data_case,
        generate_long_mixed_text_case,
    ]

    # 5 examples per scenario.
    for generator in scenario_generators:
        for _ in range(5):
            examples.append(generator(example_id))
            example_id += 1

    save_jsonl(examples, OUTPUT_PATH)


if __name__ == "__main__":
    generate_evaluation_dataset()