# Phase F — AI Architecture

Principle: **AI reads only projected facts + evidence; it never sources truth.**
Every AI subsystem = Prompt + Retrieval(RAG/KG) + Guardrails + Confidence +
Fallback. Reuse `llm_client` (multi-provider, GROQ live), `feature_store`,
`evidence_graph`, `intent_analyzer`.

## Cross-cutting stack
- **Retrieval:** hybrid search (Phase D) → top-K rows with evidence → context.
- **KG hop:** for relational questions, traverse Knowledge Graph (Phase G) and
  serialize the subgraph into the prompt (facts + edges).
- **Guardrails:** (1) answer only from provided context; (2) cite evidence ref for
  every claim; (3) refuse/hedge when confidence < threshold; (4) never state a
  GOV fact not present in retrieval; (5) PII redaction on ingest to prompt.
- **Confidence:** blended from retrieved-fact confidences + coverage; surfaced to UI.
- **Memory:** per-conversation short-term (last N turns) + per-user profile facts
  (structured, not raw chat) in `AIConversation`. **Caching:** prompt-cache +
  semantic response cache keyed by (intent, entity, params).
- **Fallback:** deterministic templated answer from the same facts if LLM down.

## Subsystems
| # | AI | Retrieval | Grounding | Output | Guardrail focus |
|---|---|---|---|---|---|
| 1 | **AI Chat** | hybrid+KG | DB facts+evidence | cited answer | no generic ChatGPT; cite or refuse |
| 2 | **AI Search** | intent→facets/vector | index | ranked+facets | parse not invent |
| 3 | **AI Recommendations** | feature_store | Phase E | ranked+why | evidence per item |
| 4 | **AI Predictions** | time-series | job_snapshots/trends | value+CI | show basis + confidence |
| 5 | **AI Resume** | doc parse | candidate profile | structured JSON + score | PII stays tenant-scoped |
| 6 | **AI Matching** | vectors | job↔candidate | match%+gaps | deterministic core, LLM explains |
| 7 | **AI Interview Coach** | job+candidate | role reqs | Q&A prep | no fabricated company facts |
| 8 | **AI Visa Advisor** | KG hop | sponsor register+routes | route + probability + evidence | **never guess visa law**; cite register |
| 9 | **AI Employer Intelligence** | employer rollups | trends/news | brief + risks | cite sources |
| 10 | **AI Company Intelligence** | enrichment | website/tech/socials | profile | cite provenance |

## Visa Advisor (flagship) — no-hallucination contract
```
Q: "Can Company X sponsor me for a care role?"
→ retrieve: sponsor_licences[X], routes, occupation map, recent jobs, salary threshold
→ compute: rule score → probability
→ answer: "92% — X holds an active Skilled Worker licence (verified in the UK
   register, last updated <date>), posted 4 care roles in 90d, salary above the
   route threshold." Confidence 97%. [evidence: licence_id, job_ids]
→ if no licence row: "No sponsor licence found for X in the current register" (never a guess)
```

## Model routing (cost-aware, reuse llm_client)
Cheap/local (GROQ/Haiku-class) for intent, extraction, personalization; larger
model only for complex advisory. Every call budget-tagged; batch where possible.
