# Enterprise Solution Design — Wild Automations (Jobs & Visa Intelligence)

Architecture-only. No production code until every doc here is approved.
Grounded in the current codebase; reuse-first (see `../ARCHITECTURE_DDD.md`).

| Phase | Doc | Scope |
|---|---|---|
| A | [A-entity-catalog.md](A-entity-catalog.md) | Enterprise entity catalog (per-entity governance sheet) |
| B | [B-data-dictionary.md](B-data-dictionary.md) | Master field dictionary |
| C | [C-data-lineage.md](C-data-lineage.md) | Source → clean → normalize → enrich → store → search → AI → UI → export |
| D | [D-search-architecture.md](D-search-architecture.md) | Global/semantic/vector/keyword/faceted/geo search + index map |
| E | [E-recommendation-engine.md](E-recommendation-engine.md) | Recommender designs (inputs/outputs/scoring/evidence) |
| F | [F-ai-architecture.md](F-ai-architecture.md) | 10 AI subsystems (prompt/RAG/KG/guardrails/confidence) |
| G | [G-knowledge-graph-spec.md](G-knowledge-graph-spec.md) | Nodes/edges/algorithms/embeddings |
| H | [H-dashboard-catalog.md](H-dashboard-catalog.md) | 8 dashboards, per-widget spec |
| I | [I-feature-data-matrix.md](I-feature-data-matrix.md) | Feature → data/scraper/AI/event/permission |
| J | [J-risk-migration-ops.md](J-risk-migration-ops.md) | Risk, migration, perf, scale, cost, security, monitoring, testing, DR |

Convention: every entity/field is grounded in a **Source of Truth** (scraper /
gov register / API / derived / AI) and carries **confidence**. AI never writes to
a gov-sourced field.
