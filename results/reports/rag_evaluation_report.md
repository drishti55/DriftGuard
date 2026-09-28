# DriftGuard Evaluation Report — RAG Mode

## Drift Detection (Binary)
| Metric | Value |
|--------|-------|
| Accuracy | 0.4 |
| Precision | 0.5 |
| Recall | 0.3333 |
| F1-Score | 0.4 |
| False Positive Rate | 0.5 |
| False Negative Rate | 0.6667 |
| Total Cases | 5 |

## Drift Classification
| Metric | Value |
|--------|-------|
| Accuracy | 0.4 |
| Macro-F1 | 0.28 |

### Per-Class Metrics
| Drift Type | Precision | Recall | F1 | Support |
|-----------|-----------|--------|-----|---------|
| api_spec_vs_code | 0.0 | 0.0 | 0.0 | 1 |
| ci_vs_project | 0.0 | 0.0 | 0.0 | 1 |
| docker_vs_project | 0.0 | 0.0 | 0.0 | 0 |
| documentation_vs_code | 1.0 | 1.0 | 1.0 | 1 |
| no_drift | 0.3333 | 0.5 | 0.4 | 2 |

## Severity Prediction
| Metric | Value |
|--------|-------|
| Accuracy | 0.4 |
| Macro-F1 | 0.1429 |

## Evidence Quality
| Metric | Value |
|--------|-------|
| Mentions Artifacts | 0.2 |
| Substantive | 0.8 |
| Mentions Identifiers | 0.0 |
| Verified Citation Rate | 0.0 |

## LLM Inference Stats
| Metric | Value |
|--------|-------|
| Total Calls | 5 |
| Parse Success Rate | 100.0%
| Avg Latency | 23.4s
| Fallbacks Used | 0 |
