# Evaluation report

## Metrics by scenario

| Scenario | N | Support | Precision | Recall | F1-score | Miss rate |
|---|---:|---:|---:|---:|---:|---:|
| abbreviations | 5 | 30 | 96.77% | 100.00% | 98.36% | 0.00% |
| dni_missing_letter | 5 | 10 | 100.00% | 100.00% | 100.00% | 0.00% |
| long_mixed_text | 5 | 40 | 95.24% | 100.00% | 97.56% | 0.00% |
| sensitive_clinical_data | 5 | 10 | 100.00% | 100.00% | 100.00% | 0.00% |
| standard | 5 | 35 | 100.00% | 100.00% | 100.00% | 0.00% |
| typos | 5 | 30 | 96.77% | 100.00% | 98.36% | 0.00% |
| unlabelled_identifiers | 5 | 20 | 95.24% | 100.00% | 97.56% | 0.00% |
| **TOTAL** | 35 | 175 | 97.22% | 100.00% | 98.59% | 0.00% |

## Global interpretation

Overall results across **35 examples** and **175 expected entities**: Precision 97.22%, Recall 100.00%, F1-score 98.59%.

The best-performing scenarios were `dni_missing_letter`, `sensitive_clinical_data`, `standard` with an F1-score of 100.00%.
The most challenging scenarios were `long_mixed_text`, `unlabelled_identifiers` with an F1-score of 97.56%.

These results allow us to identify the conditions under which the local LLM-based de-identification system is more reliable and the cases where further improvements would be required.

## Metrics by entity type

| Entity type | Support | Precision | Recall | F1-score | Miss rate |
|---|---:|---:|---:|---:|---:|
| DIRECCIÓN | 20 | 100.00% | 100.00% | 100.00% | 0.00% |
| DNI | 30 | 100.00% | 100.00% | 100.00% | 0.00% |
| EMAIL | 25 | 100.00% | 100.00% | 100.00% | 0.00% |
| FECHA | 35 | 100.00% | 100.00% | 100.00% | 0.00% |
| NOMBRE | 40 | 100.00% | 100.00% | 100.00% | 0.00% |
| TELÉFONO | 25 | 83.33% | 100.00% | 90.91% | 0.00% |
| **TOTAL** | 175 | 97.22% | 100.00% | 98.59% | 0.00% |

# Error analysis

## Scenario: abbreviations

- False positives: 1
- False negatives: 0

### Examples of false positives
- `970-1065x133` classified as `TELÉFONO`

## Scenario: typos

- False positives: 1
- False negatives: 0

### Examples of false positives
- `837-9176` classified as `TELÉFONO`

## Scenario: unlabelled_identifiers

- False positives: 1
- False negatives: 0

### Examples of false positives
- `275-2735x4549` classified as `TELÉFONO`

## Scenario: long_mixed_text

- False positives: 2
- False negatives: 0

### Examples of false positives
- `490-9133x41232` classified as `TELÉFONO`
- `871-5451x6808` classified as `TELÉFONO`
