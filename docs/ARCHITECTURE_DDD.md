# Wild Automations — DDD Architecture, ER Model, Knowledge Graph & Event Flow
### Recruitment + Global Visa Intelligence Platform · Jobs domain
> Design artifact. No implementation yet. Grounded in the current codebase
> (audit) with an explicit reuse map so we extend, never duplicate.

---

## 0. Reuse map (what already exists → where it lands)
| Existing | DDD home |
|---|---|
| `core/jobspy_client, ats_client, gulftalent_client, uk_jobs_client` | Ingestion Context — **inbound adapters** (wrapped to emit events) |
| `core/ai_analyzer._score_job` (salary→USD, tax, appeal) | Intelligence Context — **domain service** |
| `core/entity_resolver` + `entity_registry` (leads) | Employer/Job Context — **resolution pattern reused** |
| `core/event_timeline.py` (Wave 5 events table) | **Event store foundation — already exists** |
| `core/store.py`, `database_layer.py`, `supabase_leads.py` | Infrastructure — **repositories** |
| `migrations/*.sql` (Supabase) | ER schema **home** |
| `delivery/*` (WhatsApp/Meta) | Notification Context — **outbound adapter** |
| `feature_store`, `evidence_graph` | Intelligence + Knowledge Graph substrate |

---

## 1. Bounded Contexts (DDD context map)
```
                         ┌──────────────────────────┐
                         │   INGESTION (supporting)  │  scrapers as adapters
                         │  JobSpy·ATS·GulfTalent·UK  │  emits RawJobScraped
                         └────────────┬──────────────┘
                                      │ RawJobScraped
        ┌───────────────┬────────────┼───────────────┬──────────────┐
        ▼               ▼            ▼                ▼              ▼
┌──────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│  JOB (core)  │ │ EMPLOYER   │ │ SPONSOR &  │ │  GEO /     │ │ CANDIDATE  │
│ posting,     │ │ company,   │ │ VISA (CORE │ │ COUNTRY    │ │ profile,   │
│ dedup, salary│ │ branches,  │ │ = the moat)│ │ region,    │ │ skills,    │
│ normalization│ │ enrichment │ │ licence,   │ │ city,      │ │ prefs      │
│              │ │            │ │ routes     │ │ policy     │ │            │
└──────┬───────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
       └────────────────┴─────────────┴──────────────┴──────────────┘
                                      │ (facts)
                         ┌────────────▼──────────────┐
                         │  INTELLIGENCE (core)      │ evidence-backed scoring,
                         │  scoring·trends·prediction │ visa-probability, confidence
                         └────────────┬──────────────┘
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ SEARCH/QUERY │ │ NOTIFICATION │ │  DASHBOARDS  │  read models
            │ (read models)│ │ WhatsApp subs│ │  (projections)│
            └──────────────┘ └──────────────┘ └──────────────┘
```
**Core domains** (the defensible IP): **Sponsor & Visa** + **Intelligence**.
Everything else is supporting/generic.

---

## 2. Aggregates, Entities, Value Objects
**Aggregate roots** own invariants and are the only transactional boundaries.

- **Employer** (root): identity(name+domain), industry, size, website, linkedin;
  owns *Branches*; references *SponsorLicence*. Invariant: one canonical employer
  per (normalized name + country).
- **SponsorLicence** (root, Sponsor context): licence_id, employer_ref, town,
  county, **routes[]** (Skilled Worker, GBM…), tier (A/B), status, first_seen,
  last_verified. Source of truth = UK Gov register. Invariant: status/route only
  change via a register refresh event (never AI).
- **Job** (root): job_id, employer_ref, title, *Location* (VO), *Salary* (VO),
  posted_at, source, description, *skills[]*, seniority, remote, visa_flag.
  Invariant: deduped by (employer + normalized title + location).
- **Country** (root): iso, region, cities[], visa_types[], policy snapshot.
- **Candidate** (root, later): passport, nationality, skills, experience, prefs.

**Value Objects** (immutable, no identity):
`Salary(min,max,currency,period,usd_annual,take_home)` · `Location(city,region,
country_iso,remote)` · `VisaRoute(code,name,category)` · `Confidence(0..1)` ·
`Score(value,components,evidence[])` · `Money`.

**Domain Services** (logic that isn't one entity):
`SalaryNormalizer` · `EmployerResolver` · `SponsorMatcher` (job↔licence join) ·
`JobScorer` (reuse `ai_analyzer._score_job`) · `TrendCalculator` ·
`VisaProbabilityService` (evidence-backed).

---

## 3. Entity Relationship Model (relational — Supabase/Postgres)
```
countries ──1:N── regions ──1:N── cities
   │                                  │
   │                                  ▼
   │                             employers ──1:N── branches
   │                                  │  1:1(optional)
   │                                  ▼
   │                          sponsor_licences ──M:N── visa_routes   (sponsor_licence_routes)
   │                                  │
   ▼                                  ▼
visa_types                          jobs ──1:N── job_snapshots        (time-series → trends)
                                     │  M:N── skills  (job_skills)
                                     │  1:1── salaries
                                     ▼
                                  matches ──N:1── candidates ──M:N── skills (candidate_skills)

events  (append-only event store — already exists as event_timeline)
subscriptions (country/company/salary/visa filters → WhatsApp)
```
**Key tables & the critical foreign keys**
- `employers(id, canonical_name, domain, industry, size, website, linkedin, country_iso, first_seen)`
- `sponsor_licences(id, employer_id FK, licence_name, town, county, tier, status, first_seen, last_verified)`
- `visa_routes(id, code, name, category)` · `sponsor_licence_routes(licence_id, route_id)`
- `jobs(id, employer_id FK, title, seniority, location_city, country_iso, remote, salary_id FK, posted_at, source, visa_flag, description_hash, first_seen)`
- `job_snapshots(id, job_id FK, seen_at, still_open, source)`  ← powers hiring-trend
- `salaries(id, min, max, currency, period, usd_annual, take_home_usd)`
- `skills(id, name)` · `job_skills(job_id, skill_id, weight)`
- `job_intelligence(job_id FK, visa_probability, confidence, ai_score, risk, evidence jsonb, computed_at)`

**The moat query** (already-collected data, just unjoined today):
`jobs ⋈ employers ⋈ sponsor_licences ⋈ visa_routes` →
"This job at *X* is **visa-sponsorable via Skilled Worker** (licence active, tier A)."

---

## 4. Knowledge Graph (nodes + typed edges)
```
(Country)                         (Industry)          (Skill)
   ▲  IN                             ▲ IN_INDUSTRY       ▲ REQUIRES
   │                                 │                   │
(City) ◄─LOCATED_IN─ (Employer) ─POSTED─► (Job) ─OFFERS─► (Salary)
                        │                    │
                     HOLDS                SPONSORED_VIA
                        ▼                    ▼
              (SponsorLicence) ─GRANTS─► (VisaRoute) ─VALID_FOR─► (Country)
                        │
                   RENEWED_ON (time) → trend edges

(Candidate) ─HAS─► (Skill)      (Candidate) ─MATCHES{score}─► (Job)
(Candidate) ─PREFERS─► (Country)
```
**Why a graph, not just tables:** enterprise queries are *traversals* —
"employers in Manchester that sponsor Skilled Worker in Healthcare, hiring more
this quarter, salary > £30k" = a 4-hop path. We materialize this from the ER
model into a graph projection (reuse `evidence_graph` node/edge substrate).

**Edge properties carry the intelligence:** `MATCHES{score, confidence}`,
`SPONSORED_VIA{probability, evidence}`, `POSTED{count_90d, trend}`.

---

## 5. Event-Driven Data Flow (event store already exists)
**Domain events** (past-tense facts, append-only in `events`):
```
RawJobScraped ─► JobNormalized ─► EmployerResolved ─► SponsorLicenceRefreshed
      │                │                 │                     │
      └──────────► JobSponsorLinked ◄────┴─────────────────────┘
                        │
                   JobScored ─► TrendComputed ─► MatchFound ─► SubscriptionTriggered
```
**Pipeline (choreography):**
```
Scraper adapter ──emit──► RawJobScraped
  Normalizer         (SalaryNormalizer + Location VO) ──► JobNormalized
  EmployerResolver   (canonical employer, dedup)       ──► EmployerResolved
  SponsorLinker      (join UK register index)           ──► JobSponsorLinked
  IntelligenceScorer (JobScorer + VisaProbability)      ──► JobScored
  Projector          (write read models / KG)           ──► (search, dashboards)
  Notifier           (match vs subscriptions)           ──► WhatsApp digest
```
**Guarantees:** each handler is idempotent (keyed by job hash); the event store
is the source of truth; **read models are rebuildable** by replaying events —
this is what makes trends/predictions possible (time-series from `job_snapshots`
+ event history). AI reads *only* projected facts → **never hallucinates**.

---

## 6. Hexagonal layering (target folder structure)
```
domain/            entities, value_objects, events, domain_services (pure, no I/O)
  jobs/  employer/  sponsor/  intelligence/  geo/
application/       use-cases (commands + queries), event handlers
infrastructure/    scraper adapters, repositories (Supabase), event_bus, KG store
interface/         FastAPI routes, WhatsApp, dashboards
```
Dependency rule: `interface → application → domain ← infrastructure`.
Domain has **zero** framework/DB imports (testable in isolation).

---

## 7. Migration strategy (strangler — no big-bang)
1. Introduce `domain/` + event contracts **alongside** current code.
2. Wrap existing scrapers as adapters emitting `RawJobScraped` (behavior unchanged).
3. Stand up the ER tables in Supabase migrations; dual-write from the pipeline.
4. Move `_score_job` into `intelligence` domain service (pure).
5. Cut `/api/jobs/all` to read from projections; retire the flat path last.

---

## 8. Business value & priority (SaaS-founder lens)
| Capability | Enterprise value | Complexity | Priority |
|---|---|---|---|
| Sponsor↔Job "Visa Verified" join | 🟢🟢🟢 (the product) | Low (data exists) | **P0** |
| Relational ER + event store | Foundation for everything | Med | **P0** |
| Weekly scheduler → job_snapshots → trends | Predictions unlock | Med | **P1** |
| Knowledge-graph query API | Enterprise search/traversal | Med-High | **P1** |
| Evidence-backed AI + WhatsApp subs | Retention + upsell | Med | **P2** |

**North star:** the defensible asset is the **Sponsor/Visa + Intelligence** core —
official gov data joined to live jobs, as an event-sourced knowledge graph.
```
```
