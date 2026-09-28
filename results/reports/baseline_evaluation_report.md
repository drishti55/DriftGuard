# DriftGuard Evaluation Report — BASELINE Mode

## Drift Detection (Binary)
| Metric | Value |
|--------|-------|
| Accuracy | 0.8 |
| Precision | 1.0 |
| Recall | 0.7647 |
| F1-Score | 0.8667 |
| False Positive Rate | 0.0 |
| False Negative Rate | 0.2353 |
| Total Cases | 20 |

## Drift Classification
| Metric | Value |
|--------|-------|
| Accuracy | 0.55 |
| Macro-F1 | 0.5694 |

### Per-Class Metrics
| Drift Type | Precision | Recall | F1 | Support |
|-----------|-----------|--------|-----|---------|
| api_spec_vs_code | 1.0 | 1.0 | 1.0 | 1 |
| ci_vs_project | 0.25 | 0.3333 | 0.2857 | 3 |
| dependency_vs_code | 0.5 | 0.5 | 0.5 | 4 |
| docker_vs_project | 1.0 | 0.6667 | 0.8 | 3 |
| documentation_vs_code | 1.0 | 0.6667 | 0.8 | 3 |
| no_drift | 0.4286 | 1.0 | 0.6 | 3 |
| test_vs_code | 0.0 | 0.0 | 0.0 | 3 |

## Severity Prediction
| Metric | Value |
|--------|-------|
| Accuracy | 0.5 |
| Macro-F1 | 0.3926 |

## Evidence Quality
| Metric | Value |
|--------|-------|
| Mentions Artifacts | 0.7 |
| Substantive | 1.0 |
| Mentions Identifiers | 0.35 |

## LLM Inference Stats
| Metric | Value |
|--------|-------|
| Total Calls | 20 |
| Parse Success Rate | 100.0%
| Avg Latency | 41.8s
| Fallbacks Used | 0 |
