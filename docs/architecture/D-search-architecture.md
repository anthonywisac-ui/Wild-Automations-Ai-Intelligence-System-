# Phase D — Search Architecture

Polyglot search: **Postgres (Supabase) = system of record + keyword/faceted/geo**,
**pgvector = semantic/vector**, **KG projection = traversal**. No separate cluster
until scale demands (cost discipline). Optional future: OpenSearch for very large
keyword workloads.

## Index map (which index powers which search)
| Search | Powered by | Index | Notes |
|---|---|---|---|
| **Keyword** (title/company/desc) | Postgres FTS | `tsvector` GIN on title+desc | ranked `ts_rank` |
| **Fuzzy** (name typos) | pg_trgm | GIN trgm on canonical_name, licence_name | employer/sponsor lookup |
| **Faceted** (seniority, remote, visa, salary band, country, industry) | Postgres | btree per facet + partial idx | filter + counts |
| **Geo** (city/country/radius) | Postgres | `country_iso`, `city_id`; PostGIS if radius | remote flag special-cased |
| **Semantic / Vector** | pgvector | `ivfflat` on embeddings(title+desc, 768/1536d) | cosine; "jobs like this" |
| **Skill** | join + vector | `job_skills` + skill embeddings | skill-expansion (React→JS) |
| **Sponsor** | Postgres + in-mem index | licence_name trgm, status | verified-only filter |
| **Employer** | Postgres | canonical_name trgm, domain | rollup counts |
| **Visa/Country** | reference join | route/country tables | policy-aware |
| **Candidate** (later) | pgvector | resume embedding | recruiter search |
| **Global** (one box → everything) | **router** | fan-out to above + rank fusion | see below |

## Global search (the "one search box")
```
query ─► intent classifier (rules + tiny LLM) ─►
   ├─ entity route?  → keyword+fuzzy on employers/sponsors/jobs
   ├─ natural lang?  → embed → vector search (jobs/candidates)
   ├─ filter phrase? → parse facets ("skilled worker jobs in manchester >£30k")
   └─ fuse results (Reciprocal Rank Fusion) → re-rank by JobIntelligence.ai_score
```
- **Hybrid ranking:** `score = w1·bm25 + w2·cosine + w3·ai_score + w4·freshness + w5·visa_verified`.
- **Facets returned** with every query (counts) for the filter rail.
- **Latency budget:** p95 < 300ms keyword/faceted, < 500ms hybrid.

## Semantic pipeline
- Embed `title + norm_title + skills + description[:1k]` on `JobScored` event.
- Store vector in `jobs.embedding` (pgvector). Nightly reindex ivfflat lists.
- "Similar jobs", "jobs matching this CV", "companies like X" all reuse this.

## Query→AI bridge (feeds Phase F)
Search results (with evidence) are the **retrieval layer** for AI chat/advisor —
RAG grounds every answer in ranked rows, never free ChatGPT.
