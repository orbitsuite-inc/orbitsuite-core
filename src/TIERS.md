# OrbitSuite Tiers Detail

This document expands the feature matrix to clarify value differentiation.

## Summary Taglines
- **Core**: Minimal open foundation.
- **Pro**: Local models + reliability toolkit.
- **Enterprise**: Scale, governance & memory intelligence.

## Pillars & Features

### 1. Model & Execution Control
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| OpenAI adapter | ✓ | ✓ | ✓ |
| Local model adapters (llama.cpp/Ollama/HTTP) | — | ✓ | ✓ |
| Model routing / cost-aware selection | — | ✓ | ✓ |
| GPU configuration helpers | — | ✓ | ✓ |
| Multi-node execution | — | — | ✓ |

### 2. Memory & Context
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Ephemeral in-process context | ✓ | ✓ | ✓ |
| Session extension helpers | — | ✓ | ✓ |
| Mnemonic Token System (multi-tier) | — | — | ✓ |
| Vector index + RAG recall | — | — | ✓ |

### 3. Reliability & Observability
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Stdout logging | ✓ | ✓ | ✓ |
| Structured JSON logging | — | ✓ | ✓ |
| Retries with backoff | — | ✓ | ✓ |
| Fallback routing | — | ✓ | ✓ |
| Log rotation | — | ✓ | ✓ |
| Traces / metrics dashboards | — | — | ✓ |

### 4. Architecture & Planning
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Basic pattern recommendation | ✓ | ✓ | ✓ |
| Component synthesis (detailed) | — | ✓ | ✓ |
| Risk assessment & roadmap | — | ✓ | ✓ |
| Compliance & security hooks | — | — | ✓ |

### 5. Security & Compliance
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Basic safe defaults | ✓ | ✓ | ✓ |
| Security Guard agent | — | — | ✓ |
| Entropy Monitor agent | — | — | ✓ |
| Sandbox Enforcement agent | — | — | ✓ |
| Policy engine / signed manifests | — | — | ✓ |
| Audit trails | — | — | ✓ |

### 6. Orchestration & Integration
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Single-process orchestrator | ✓ | ✓ | ✓ |
| Enhanced local workflow features | — | ✓ | ✓ |
| Queue / fleet management | — | — | ✓ |
| Job snapshots & revert | — | — | ✓ |
| Webhook endpoints | — | — | ✓ |
| External-store autosync (Git/Gist) | — | — | ✓ |
| Offline / on-prem mode | — | — | ✓ |

### 7. Governance & Operations
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Basic license check | — | ✓ | ✓ |
| Capability / entitlement gating | — | — | ✓ |
| Role-based agent access (RBAC) | — | — | ✓ |
| Telemetry export | — | — | ✓ |
| Advanced log pipelines | — | — | ✓ |

### 8. User & Support Experience
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Community support | ✓ | ✓ | ✓ |
| Email support | — | ✓ | ✓ |
| SLA & guided onboarding | — | — | ✓ |
| OrbitCockpit (basic surfaces) | — | ✓ | ✓ |
| Live fleet dashboards / hardware panel | — | — | ✓ |

## Upgrade Hints
Core responses may include a single `upgrade_hint` key (optional) to signal available enhancements. This can be removed programmatically if undesired.

## Migration Philosophy
- Additive: higher tiers are supersets; no breaking schema changes.
- Deterministic Core: ensures trust & auditability.
- Seam continuity: identical method names enable drop-in replacement.

## When to Upgrade
| Symptom | Recommended Tier |
| ------- | ---------------- |
| Need offline / local-only inference | Pro |
| Latency & cost optimization across models | Pro |
| Cross-task long-term memory & semantic recall | Enterprise |
| Governance / audit mandates | Enterprise |
| Multi-team scaling & queue orchestration | Enterprise |
| Production SLAs & support | Enterprise |

## Contact
Reach out to obtain Pro / Enterprise licensing and distribution packages.
