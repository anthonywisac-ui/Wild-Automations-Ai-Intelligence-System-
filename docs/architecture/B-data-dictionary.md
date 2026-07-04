# Phase B — Master Data Dictionary

Field-level spec. Columns: **Type · Null · Uniq · Idx · FK · Der(ived) · AI ·
SoT(source) · Confidence · Validation/Normalization · Used-by**. Fully specified
for the core jobs/visa tables; the same standard applies to every table in
Phase A. SoT codes: SCR=scraper, GOV=gov register, API, DER, AI, USR.

---

## employers
| Field | Type | Null | Uniq | Idx | FK | Der | AI | SoT | Conf | Validation / Normalization | Used by |
|---|---|---|---|---|---|---|---|---|---|---|---|
| employer_id | uuid | N | Y | Y | — | — | — | sys | — | v4 | all |
| canonical_name | text | N | — | trgm | — | Y | — | DER | 0.6–.99 | trim, collapse ws, strip Ltd/Inc for match key | search, KG, UI |
| domain | text | Y | Y | Y | — | Y | — | DER/API | .8 | lowercase, registrable domain | logo fetch, dedup |
| industry_id | int | Y | — | Y | industries | — | Y | AI/REF | .7 | map to SIC/NAICS | facets, analytics |
| size | text | Y | — | — | — | — | — | API/enrich | .5 | band: 1-10…10k+ | UI, scoring |
| website / linkedin | text | Y | — | — | — | — | — | API/enrich | .6 | URL validate | UI, enrichment |
| country_iso | char2 | N | — | Y | countries | — | — | DER | .9 | ISO-3166 | geo search |
| first_seen | timestamptz | N | — | Y | — | — | — | sys | — | — | trends |

## sponsor_licences  (GOV — 1.0 confidence, immutable except refresh)
| Field | Type | Null | Uniq | Idx | FK | SoT | Conf | Normalization | Used by |
|---|---|---|---|---|---|---|---|---|---|
| licence_id | uuid | N | Y | Y | — | sys | — | — | all |
| employer_id | uuid | N | — | Y | employers | DER | .9 | fuzzy-match register name → employer | join |
| licence_name | text | N | — | trgm | — | GOV | 1.0 | as-published | sponsor search |
| town / county | text | Y | — | Y | — | GOV | 1.0 | title-case | geo |
| tier | text | Y | — | — | — | GOV | 1.0 | enum {Worker,Temporary} | filter |
| status | text | N | — | Y | — | GOV | 1.0 | {active,revoked,expired} SCD-2 | verified badge |
| first_seen / last_verified | timestamptz | N | — | Y | — | sys | — | — | freshness, trend |

## jobs
| Field | Type | Null | Idx | FK | Der | AI | SoT | Conf | Validation/Normalization | Used by |
|---|---|---|---|---|---|---|---|---|---|---|
| job_id | uuid | N | Y | — | — | — | sys | — | — | all |
| employer_id | uuid | N | Y | employers | Y | — | DER | .8 | resolver | join, facets |
| title | text | N | tsv | — | — | — | SCR | 1.0 | trim; keep raw + `norm_title` | search, match |
| norm_title | text | N | Y | — | Y | — | DER | .9 | lowercase, seniority-strip → canonical role | dedup, benchmark |
| seniority | text | Y | Y | — | Y | AI | DER/AI | .7 | {intern,junior,mid,senior,lead} | facet, scoring |
| city / country_iso | text | Y | Y | cities | Y | — | DER | .8 | split "City, Country"; ISO map | geo search |
| remote | bool | Y | Y | — | Y | — | DER | .8 | detect remote/onsite/hybrid | facet |
| salary_id | uuid | Y | — | salaries | — | — | DER | — | see salaries | UI, scoring |
| posted_at | timestamptz | Y | Y | — | Y | — | SCR/DER | .7 | parse "10 Hours ago"/ISO → ts | sort, freshness |
| source | text | N | Y | — | — | — | SCR | 1.0 | scraper name (the "mention") | provenance chip |
| visa_flag | bool | Y | Y | — | — | — | SCR | .8 | from gulftalent/uk field | filter |
| description_hash | text | N | Y | — | Y | — | DER | — | sha256(desc) | change detect |

## salaries  (normalizer — reuse `ai_analyzer._extract_salary_usd`)
| Field | Type | SoT | Normalization |
|---|---|---|---|
| min/max/currency/period | num/text | DER | parse ranges, /month→/yr, FX to USD |
| usd_annual | num | DER | midpoint annualized USD |
| take_home_usd | num | DER | apply `_tax_for(location)` (already coded) |

## job_intelligence  (AI/derived — every field carries confidence + evidence)
| Field | Type | AI | SoT | Conf | Meaning |
|---|---|---|---|---|---|
| visa_probability | num 0..1 | Y | DER | self | P(this job is visa-sponsorable) from sponsor join |
| ai_score | num 0..1 | Y | DER | self | overall opportunity (reuse universal_appeal) |
| risk | num 0..1 | Y | AI | self | stale/low-signal/unverified employer |
| expected_salary | num | Y | AI | self | benchmark(role×country×seniority) |
| evidence | jsonb | — | DER/GOV | — | [{type,source,ref}] — every claim cited |
| model_version | text | — | sys | — | reproducibility |

## events  (append-only)
| Field | Type | Notes |
|---|---|---|
| event_id / aggregate_id / sequence | uuid/uuid/int | unique(aggregate_id,sequence) |
| type | text | RawJobScraped, JobScored, … |
| payload | jsonb | no PII |
| occurred_at | timestamptz | idx |
| schema_version | text | evolution |

**Global rules:** (1) raw scraped value is always retained beside the normalized
value; (2) any AI/derived field is nullable and confidence-tagged; (3) a
GOV-sourced field is **never** written by AI; (4) all money is stored in native +
USD; (5) all timestamps are `timestamptz` UTC.
