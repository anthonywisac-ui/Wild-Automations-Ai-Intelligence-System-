# Phase J — Risk, Migration & Operations

## 1. Implementation Risk Analysis
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Scraper fragility (JobSpy site changes) | High | Med | API fallbacks primary (already coded); health alerts; quarantine flaky source |
| Google/IG datacenter IP blocks (cloud) | High | Med | jobs scrapers are API/gov (not affected); social = residential proxy/cookie |
| Gov register CSV URL/format change | Med | High | dynamic URL finder (exists) + schema validation + last-good fallback |
| Employer entity-resolution errors | Med | High | deterministic-first + confidence + human review queue for low-conf merges |
| AI hallucination | Med | **Critical** | evidence-required guardrail; refuse < threshold; GOV fields read-only to AI |
| PII exposure (candidates/docs) | Low | **Critical** | encryption at rest, tenant RLS, redaction before prompts |
| Cost blow-up (LLM/compute) | Med | Med | model routing, caching, batch, budgets per tenant |
| Local dev env drift (uv/py) | Occurred | Low | pinned Docker 3.12; CI builds; don't rely on local |

## 2. Migration Strategy (strangler, no big-bang)
1. Add `domain/` + event contracts beside current code (no behavior change).
2. Wrap scrapers as adapters emitting `RawJobScraped`.
3. Create ER tables in `migrations/` (Supabase); **dual-write** from pipeline.
4. Move `_score_job` → intelligence domain service.
5. Cut `/api/jobs/all` to read projections; retire flat path last.
Each step independently shippable + reversible.

## 3. Backward Compatibility
- Existing endpoints (`/api/jobs/all`, `/jobs`, `/concierge`, dashboards) keep working
  throughout; new fields are additive/nullable.
- SQLite remains the local/fallback store; Supabase is durable primary (already wired).
- Read models are additive; old readers unaffected.

## 4. Performance Strategy
- Read/write split: writes → event store; reads → projections (denormalized).
- Indexed facets + pgvector ivfflat; p95 budgets (Phase D).
- Async ingestion; batch scraper runs; idempotent handlers.
- Cache tiers: in-mem sponsor index, Redis (future) for hot read models, HTTP cache for exports.

## 5. Scaling Strategy
- Stateless API (horizontal on Railway/containers); event store as backbone.
- Partition `job_snapshots`/`events` by month; archive cold partitions.
- Scraper workers scale independently (queue per source).
- Graph: Postgres adjacency → native graph DB only when traversal p95 degrades.

## 6. Cost Strategy
- Prefer free/gov/API sources (already the case for jobs).
- LLM: cheap-model routing + prompt/response cache + budgets.
- Storage: JSONB + partition pruning; cold archive to object storage.
- Avoid premium infra until MRR justifies (SQLite/Supabase free-tier → paid on traction).

## 7. Security Strategy
- Multi-tenant **RLS** (Supabase policies exist in `migrations/004_rls_policies.sql`).
- RBAC (Role/Permission); API keys stored hashed, scoped, rotatable.
- Secrets only in env (Railway vars); `.env` gitignored (verified).
- PII: encryption at rest, redaction to prompts, right-to-erasure job.
- Audit log (`003_audit_logs.sql`) for sensitive actions.

## 8. Monitoring Strategy
- Scraper health (pass/fail/latency) from events → Ops dashboard.
- Data freshness & dedup-rate metrics; drift alerts on gov schema.
- AI: cost, latency, cache-hit, refusal-rate, confidence distribution.
- SLOs: ingestion freshness, search p95, uptime; alert to WhatsApp/email.

## 9. Testing Strategy
- Domain layer: pure unit tests (no I/O) — high coverage on scoring/resolution/normalization.
- Contract tests per scraper adapter (fixture payloads → expected records).
- Golden-dataset + release gates (pattern already built in `tests/release_gates.py`):
  dedup rate, sponsor-join precision, no-hallucination, evidence coverage.
- Replay tests: rebuild read models from events → assert equality.
- E2E on `/jobs`, dashboards (Playwright) at breakpoints.

## 10. Disaster Recovery
- Event store = source of truth → **rebuild any projection by replay**.
- Supabase automated backups + PITR; export snapshots to object storage weekly.
- Gov register: keep last N weekly CSVs (immutable) → re-derive sponsor state.
- Runbook: restore DB → replay events → rebuild read models/graph → verify gates.
- RPO ≤ 24h, RTO ≤ 4h (target).

---
## Gate to implementation
Begin coding **only** after A–J are approved. First slice (post-approval) =
Phase-I P0: `domain/` skeleton + event contracts + **Sponsor↔Job Visa-Verified
join** (data exists today), behind additive endpoints, fully tested.
