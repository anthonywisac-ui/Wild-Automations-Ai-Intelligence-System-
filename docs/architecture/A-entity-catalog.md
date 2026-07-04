# Phase A — Enterprise Entity Catalog

Governance sheet per entity. Core jobs/visa entities are fully specified; the
full register (all ~45 entities) follows in the catalog table. Legend for
**Source of Truth (SoT)**: GOV=government register, SCR=scraper, API=partner API,
DER=derived/calculated, AI=model-generated, USR=user input.

---

## Fully-specified core entities

### Employer
- **Purpose:** canonical company that posts jobs / holds a sponsor licence.
- **PK:** `employer_id` (uuid). **Alt keys:** `(canonical_name, country_iso)`, `domain`.
- **Relationships:** 1:N Branch, 1:N Job, 1:1? SponsorLicence, N:1 Industry, N:1 Country.
- **Indexes:** `domain` (unique), `canonical_name trgm`, `country_iso`, `industry_id`.
- **Lifecycle:** created on first job/licence match → merged (dedup) → enriched → archived.
- **SoT:** name/domain=DER (resolver), industry=DER/AI, size/website=API/enrich.
- **Update freq:** on ingest (jobs) + weekly (licence). **Confidence:** 0.6–0.99 (resolver).
- **Owner:** Employer context. **Versioning:** SCD-2 on enrichment fields.
- **Soft delete:** `deleted_at` (never hard-delete; referenced by jobs).
- **Audit:** every merge/enrich emits `EmployerResolved`/`EmployerEnriched` event.
- **Caching:** hot employers cached 24h (read model). **PII:** none (org data).
- **Retention:** indefinite (reference data). **Example:** `{name:"Wrapped", domain:"wrapped.com", industry:"Software", country:"GB"}`

### SponsorLicence  (CORE / the moat)
- **Purpose:** official right of an employer to sponsor foreign workers.
- **PK:** `licence_id`. **Alt keys:** `(licence_name, town, tier)`.
- **Relationships:** N:1 Employer, M:N VisaRoute (`sponsor_licence_routes`), N:1 City.
- **Indexes:** `employer_id`, `licence_name trgm`, `status`, `(town, county)`.
- **Lifecycle:** appears in gov register → active → (renewed | revoked | expired).
- **SoT:** **GOV** (UK register CSV via `uk_jobs_client`) — immutable except by refresh.
- **Update freq:** **weekly** (register cadence). **Confidence:** 1.0 (official).
- **Owner:** Sponsor & Visa context. **Versioning:** SCD-2 (status/route history).
- **Soft delete:** never; status→`revoked` retains row (audit + trend value).
- **Audit:** `SponsorLicenceRefreshed` event per diff. **Caching:** full index in-memory (small, ~80k rows).
- **PII:** none. **Retention:** indefinite (historical sponsor trends = product value).
- **Example:** `{licence_name:"Asian African Foods Ltd", town:"London", routes:["Skilled Worker"], tier:"Worker", status:"active"}`

### Job
- **Purpose:** a single open position; the primary transactional record.
- **PK:** `job_id`. **Alt keys:** `dedup_hash = (employer_id, norm_title, city, source)`.
- **Relationships:** N:1 Employer, 1:1 Salary, M:N Skill, 1:N JobSnapshot, 1:1 JobIntelligence, N:1 VisaRoute?.
- **Indexes:** `employer_id`, `country_iso`, `posted_at`, `seniority`, `dedup_hash` (unique), `title tsvector`, `salary_usd`.
- **Lifecycle:** scraped → normalized → linked (employer+sponsor) → scored → (open|closed via snapshot).
- **SoT:** SCR (4 job scrapers); salary/skills=DER/AI. **Update freq:** per scrape run.
- **Confidence:** ingest 1.0, derived fields 0.5–0.9. **Owner:** Job context.
- **Versioning:** immutable posting + JobSnapshot time-series for changes.
- **Soft delete:** `closed_at` when snapshot shows gone. **Audit:** `JobNormalized/JobScored` events.
- **Caching:** search read-model, 15m TTL. **PII:** none (may contain recruiter email → mask).
- **Retention:** 24 months open + archive. **Example:** `{title:"Senior Backend Engineer", employer:"Facebook", city:"Dubai", salary_usd:250000, source:"GulfTalent · Remotive"}`

### JobSnapshot  (time-series — powers trends/prediction)
- **Purpose:** observation that a job was seen open at time T.
- **PK:** `snapshot_id`. **Alt keys:** `(job_id, seen_at::date, source)`.
- **Relationships:** N:1 Job. **Indexes:** `job_id`, `seen_at`.
- **SoT:** SCR. **Update freq:** every scrape. **Confidence:** 1.0. **Owner:** Job.
- **Versioning:** append-only (immutable fact). **Soft delete:** never.
- **Audit:** is itself the audit trail. **Caching:** aggregated into trends read-model.
- **PII:** none. **Retention:** 36 months (trend window). **Example:** `{job_id, seen_at, still_open:true}`

### VisaRoute
- **Purpose:** immigration route a licence can sponsor (Skilled Worker, GBM…).
- **PK:** `route_id`. **Alt keys:** `code`. **Relationships:** M:N SponsorLicence, M:N Country.
- **Indexes:** `code` (unique). **SoT:** GOV. **Update freq:** rare (policy). **Confidence:** 1.0.
- **Versioning:** SCD-2 on policy change. **Soft delete:** deprecate flag. **PII:** none.
- **Retention:** indefinite. **Example:** `{code:"SKILLED_WORKER", name:"Skilled Worker", category:"Work"}`

### JobIntelligence  (AI/derived — never overwrites facts)
- **Purpose:** scores/predictions/evidence attached to a Job (separate table = clean separation).
- **PK:** `job_id` (1:1). **Relationships:** 1:1 Job, N:1 Evidence set.
- **Fields:** visa_probability, confidence, ai_score, risk, expected_salary, evidence(jsonb), computed_at, model_version.
- **SoT:** DER/AI. **Update freq:** on `JobScored`. **Confidence:** self-reported per field.
- **Versioning:** `model_version` + recompute (idempotent). **Soft delete:** replace on recompute.
- **Audit:** `JobScored` event with evidence refs. **Caching:** with job read-model.
- **PII:** none. **Retention:** with job. **Example:** `{visa_probability:0.92, confidence:0.97, evidence:[{type:"sponsor_register", licence_id:...}]}`

### Event  (event store — reuse `event_timeline`)
- **Purpose:** append-only source of truth; enables replay/rebuild of read models.
- **PK:** `event_id`. **Alt keys:** `(aggregate_id, sequence)`. **Indexes:** `aggregate_id`, `type`, `occurred_at`.
- **SoT:** system. **Update freq:** continuous. **Confidence:** n/a. **Versioning:** immutable, `schema_version`.
- **Soft delete:** never. **Retention:** indefinite (compact/snapshot >24m). **PII:** avoid in payload.

### Tenant / User / Role / Permission / APIKey
- **Tenant** PK `tenant_id`; owns all business data (row-level isolation). SoT USR. Retention: contract+30d. Soft-delete + purge on request (GDPR).
- **User** PK `user_id`, alt `email` (unique per tenant). **PII: HIGH** (email, name). Audit all auth. Retention: account life+30d.
- **Role/Permission** RBAC; PK ids; seeded reference. **APIKey** PK `key_id`, store **hash only**, `last_used`, scopes, rotateable. PII: secret (never logged).

---

## Full entity register (catalog)
| Entity | PK | Key relationships | SoT | Update | PII | Retention |
|---|---|---|---|---|---|---|
| Region | region_id | N:1 Country, 1:N City | REF | rare | none | ∞ |
| City | city_id | N:1 Region | REF/SCR | rare | none | ∞ |
| Country | iso | 1:N Region, M:N VisaRoute | REF/GOV | quarterly | none | ∞ |
| Branch | branch_id | N:1 Employer, N:1 City | DER/enrich | on enrich | none | ∞ |
| Salary | salary_id | 1:1 Job | DER (normalizer) | on ingest | none | with job |
| Benefit | benefit_id | M:N Job | AI/parse | on ingest | none | with job |
| Skill | skill_id | M:N Job, M:N Candidate | AI/extract | on ingest | none | ∞ |
| Occupation | occ_id | N:1 OccupationGroup, M:N Job | REF (SOC/ONET) | rare | none | ∞ |
| OccupationGroup | group_id | 1:N Occupation | REF | rare | none | ∞ |
| Industry | industry_id | 1:N Employer | REF/AI | rare | none | ∞ |
| Candidate | candidate_id | M:N Skill, 1:N Application | USR | on edit | **HIGH** | account+30d |
| CandidateSkill | (cand,skill) | join | USR/AI | on edit | med | with candidate |
| Application | app_id | N:1 Candidate, N:1 Job | USR | on action | med | 24m |
| Interview | interview_id | N:1 Application | USR | on action | med | 24m |
| Document | doc_id | N:1 Candidate | USR upload | on upload | **HIGH** | account+30d, encrypted |
| CompanyIntelligence | employer_id | 1:1 Employer | DER/AI | daily | none | with employer |
| EmployerIntelligence | employer_id | 1:1 Employer | DER/AI | daily | none | with employer |
| Prediction | prediction_id | N:1 (any aggregate) | AI | on compute | none | 12m |
| Notification | notif_id | N:1 User | system | on send | low | 12m |
| Subscription | sub_id | N:1 User | USR | on edit | low | account life |
| Alert | alert_id | N:1 Subscription | system | on trigger | low | 6m |
| WhatsAppSubscription | wa_sub_id | N:1 User | USR | on edit | **med (phone)** | account life |
| EmailSubscription | em_sub_id | N:1 User | USR | on edit | med (email) | account life |
| AIConversation | conv_id | N:1 User | USR/AI | per msg | med | 6m (configurable) |
| KnowledgeNode | node_id | graph | DER | on projection | none | rebuildable |
| KnowledgeEdge | edge_id | node→node | DER | on projection | none | rebuildable |
| Evidence | evidence_id | M:N (score/prediction) | DER/GOV | on compute | none | with parent |
| Webhook | webhook_id | N:1 Tenant | USR | on edit | low(secret) | account life |
| Integration | integration_id | N:1 Tenant | USR | on edit | secret | account life |
| CRM (record) | already `records` | flat → migrating | SCR | per run | varies | per category |
