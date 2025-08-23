# Upgrading from OrbitSuite Core

This guide explains how to move from the open Core edition in this repository to the Pro or Enterprise tiers.

## 30‑Second Migration (Core -> Pro)
1. Install the commercial package or drop in the `engineer.py`, extended agents, and adapters provided under license.
2. Replace imports where needed:
   - `from engineer_core import EngineerCore` -> `from engineer import EngineerAgent`
   - Or rely on identical call sites (method names & payload keys are supersets in Pro).
3. Set environment variables for local model routing (optional):
   - `ORBITSUITE_LLM_SERVER_URL` or `ORBITSUITE_LLM_MODEL_PATH`
4. Enable structured logging (optional): `ORBITSUITE_LOG_JSON=1`
5. Run your existing workload – responses now include richer fields (e.g. `risk_assessment`, `roadmap`).

## What Changes Automatically
| Area | Core | Pro |
| ---- | ---- | --- |
| Architecture output | minimal pattern & basic components | full component spec + risks + roadmap |
| Memory | ephemeral only | session extensions (Enterprise adds multi-tier MTS) |
| Codegen | template + optional OpenAI | local adapters + routing + fallback |
| Observability | stdout prints | structured JSON logs + rotation (Enterprise adds traces) |

## Enterprise Add-On
After moving to Pro, Enterprise unlocks:
- Mnemonic Token System (multi-tier + vector recall)
- Security Guard / Entropy Monitor / Sandbox Enforcement
- Multi-node orchestration, queues, snapshots, webhooks, autosync
- Governance (RBAC, entitlement gating, policy engine)
- SLA & onboarding support

## Compatibility Contract
- All Core response keys remain valid in Pro/Enterprise.
- New keys are additive; never rely on their absence.
- Core agent methods keep the same names so imports are the only code change.

## Recommended Phased Upgrade
1. Pro (enable local LLM + logging) – validate performance & cost.
2. Add reliability flags (retries/backoff) – observe stability improvements.
3. Introduce Enterprise memory (MTS) for multi-task projects.
4. Layer governance & security agents once scaling across teams.

## Environment Flags (Examples)
| Flag | Purpose |
| ---- | ------- |
| `ORBITSUITE_VERBOSE=1` | Verbose agent dispatch logging |
| `ORBITSUITE_LLM_SERVER_URL` | Use running llama.cpp/Ollama server |
| `ORBITSUITE_LLM_MODEL_PATH` | Direct local model loading |
| `ORBITSUITE_LOG_JSON=1` | Enable structured log formatter (Pro+) |
| `ORBITSUITE_ENABLE_MTS=1` | Activate mnemonic memory (Enterprise) |

## Rollback Strategy
- Keep a branch pinned to Core. If an issue arises, revert imports in a single commit.
- Log format changes are additive; parsers should accept both until cutover.

## License & Support
Contact OrbitSuite for a commercial license key and distribution bundle.

> Core edition remains fully usable; upgrade only if you need reliability, local models, governance, or advanced memory.
