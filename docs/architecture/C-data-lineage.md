# Phase C — Data Lineage

End-to-end for the jobs/visa domain. Every stage is an event handler (Phase-5
event flow), so lineage == event replay. Reuses existing modules (noted).

## Canonical pipeline (per field lifecycle)
```
SOURCE ─► CLEAN ─► NORMALIZE ─► ENRICH ─► STORE ─► INDEX ─► CACHE ─► SEARCH ─► AI ─► UI ─► EXPORT
```

## Field-by-field lineage (representative fields)

### Job.title
- **Source:** SCR (jobspy/ats/gulftalent/uk) raw `title`.
- **Clean:** trim, unescape, collapse whitespace (reuse `core/validate`/normalizer).
- **Normalize:** derive `norm_title` (lowercase, strip seniority tokens → canonical role via occupation map).
- **Enrich:** none. **Store:** `jobs.title` (raw) + `jobs.norm_title`.
- **Index:** `title` tsvector (keyword) + norm_title for dedup/benchmark.
- **Cache:** search read-model 15m. **Search:** keyword + semantic (title embedding).
- **AI:** used in match scoring + skill extraction. **UI:** row + details. **Export:** CSV/API.

### Job.salary → salaries.usd_annual
- **Source:** SCR raw `price`/description. **Clean:** strip currency symbols/commas.
- **Normalize:** `_extract_salary_usd` (existing) → ranges, /month→/yr, FX→USD; `_tax_for` → take_home.
- **Enrich:** benchmark vs `salaries` aggregate (role×country×seniority).
- **Store:** `salaries` row (native + usd). **Index:** `jobs.salary_usd`.
- **Cache:** benchmark table nightly. **Search:** faceted range + geo. **AI:** expected_salary feature.
- **UI:** "250–320K USD". **Export:** yes.

### SponsorLicence.status  (GOV — the moat)
- **Source:** GOV UK register CSV (`uk_jobs_client._fetch_sponsor_list`, dynamic CSV URL).
- **Clean:** CSV parse, trim, dedupe by (name,town). **Normalize:** map route strings → `visa_routes.code`; town→city_id.
- **Enrich:** fuzzy-match `licence_name` → `employers.canonical_name` (resolver).
- **Store:** `sponsor_licences` SCD-2 (diff vs last week → `SponsorLicenceRefreshed`).
- **Index:** licence_name trgm, employer_id, status. **Cache:** full in-memory index (~80k, small).
- **Search:** sponsor search + employer join. **AI:** primary evidence for visa_probability.
- **UI:** "✓ Visa Sponsor Verified · Skilled Worker". **Export:** enterprise report.

### Job.employer_id  (resolution)
- **Source:** SCR raw `company`. **Clean:** strip Ltd/Inc/®. **Normalize:** canonical key.
- **Enrich:** resolver (reuse leads `entity_resolver` pattern) → existing or new Employer; domain guess.
- **Store:** FK `jobs.employer_id`. **Index:** yes. **AI:** enables employer intelligence rollups.

### JobIntelligence.visa_probability  (never hallucinated)
- **Source:** DERIVED only — join `job → employer → sponsor_licence → visa_route`.
- **Compute:** rule+weights (licence active, route match, salary ≥ threshold, recency) → probability.
- **Evidence:** every input row referenced in `evidence` jsonb. **Store:** `job_intelligence`.
- **Cache:** with job read-model. **Search:** filter "visa-verified only". **AI:** chat/advisor cite evidence.
- **UI:** badge + "Why" popover. **Export:** yes.

## Lineage guarantees
1. **Raw always retained** next to normalized (auditable, re-normalizable).
2. **Replay:** delete a read model → rebuild from `events` deterministically.
3. **Provenance:** every stored fact carries `source` + `confidence`; every derived
   fact carries `evidence[]`.
4. **No lossy overwrite:** enrichment writes new fields/rows (SCD-2), never mutates GOV data.
