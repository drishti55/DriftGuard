# DriftGuard — Baseline vs RAG Comparison

## Detection Metrics
| Metric | Baseline | RAG | Δ |
|--------|----------|-----|---|
| accuracy | 0.8 | 0.4 | -0.4000 |
| precision | 1.0 | 0.5 | -0.5000 |
| recall | 0.7647 | 0.3333 | -0.4314 |
| f1 | 0.8667 | 0.4 | -0.4667 |
| false_positive_rate | 0.0 | 0.5 | +0.5000 |
| false_negative_rate | 0.2353 | 0.6667 | +0.4314 |

## Classification Metrics
| Metric | Baseline | RAG | Δ |
|--------|----------|-----|---|
| accuracy | 0.55 | 0.4 | -0.1500 |
| macro_f1 | 0.5694 | 0.28 | -0.2894 |

## Evidence Quality
| Metric | Baseline | RAG | Δ |
|--------|----------|-----|---|
| mentions_artifacts_rate | 0.7 | 0.2 | -0.5000 |
| substantive_rate | 1.0 | 0.8 | -0.2000 |
| mentions_identifiers_rate | 0.35 | 0.0 | -0.3500 |

## Inference Stats
| Metric | Baseline | RAG |
|--------|----------|-----|
| Parse Success Rate | 1.0 | 1.0 |
| Avg Latency (s) | 41.7833890914917 | 23.43763585090637 |
| Total Cases | 20 | 5 |
