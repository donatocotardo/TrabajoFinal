from pathlib import Path
import sys

# Ensure project root is on sys.path so sibling packages like `deidentifier` are importable
sys.path.append(str(Path(__file__).resolve().parent.parent))

from deidentifier.llm_detector import detect_phi_with_ollama


example_text = """
Patient name: John Smith
Date of birth: 03/12/1985
Address: 24 Green Street, Madrid
Phone: +34 612 345 678
Email: john.smith@example.com
Visit date: 04/20/2024

Clinical note:
The patient presents with abdominal pain, nausea and mild fever.
Past medical history includes Crohn's disease.
"""


if __name__ == "__main__":
    result = detect_phi_with_ollama(example_text)

    print("Detected PHI entities:")
    for entity in result.entities:
        print(f"- {entity.text} -> [{entity.label}]")