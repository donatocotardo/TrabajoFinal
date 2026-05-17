# Evaluation report

## Metrics by scenario

| Scenario | Examples | Precision | Recall | F1-score | Failure rate |
|---|---:|---:|---:|---:|---:|
| abbreviations | 5 | 96.77% | 100.00% | 98.36% | 0.00% |
| dni_missing_letter | 5 | 100.00% | 100.00% | 100.00% | 0.00% |
| long_mixed_text | 5 | 95.24% | 100.00% | 97.56% | 0.00% |
| sensitive_clinical_data | 5 | 100.00% | 100.00% | 100.00% | 0.00% |
| standard | 5 | 100.00% | 100.00% | 100.00% | 0.00% |
| typos | 5 | 96.77% | 100.00% | 98.36% | 0.00% |
| unlabelled_identifiers | 5 | 95.24% | 100.00% | 97.56% | 0.00% |

## Global interpretation

The best-performing scenario was `dni_missing_letter` with an F1-score of 100.00%.
The most challenging scenario was `long_mixed_text` with an F1-score of 97.56%.

These results allow us to identify the conditions under which the local LLM-based de-identification system is more reliable and the cases where further improvements would be required.

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
