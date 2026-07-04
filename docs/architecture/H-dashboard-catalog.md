# Phase H — Enterprise Dashboard Catalog

Each widget: **Purpose · Calculation · Data Source · Update Freq · Filters ·
Export · API · AI**. All widgets read **projections/read-models** (never live
scrape). Freq codes: RT=on-event, H=hourly, D=daily, W=weekly.

## CEO / Executive
| Widget | Calculation | Source | Freq | AI |
|---|---|---|---|---|
| Total verified sponsors | count(sponsor_licences active) | GOV | W | — |
| Jobs indexed / new this week | count + Δ | jobs/snapshots | H | — |
| Market coverage by country | jobs·employers per country | rollup | D | — |
| Sponsorship growth trend | Δ active licences over time | SCD-2 history | W | forecast |
| Revenue vs data-value | subs × coverage | billing+data | D | — |
Filters: country/industry/date. Export: PDF/CSV. API: `/api/dash/exec`.

## Recruiter
| Widget | Calculation | Source | Freq |
|---|---|---|---|
| Hot jobs (visa-verified) | jobs where visa_probability>.8, fresh | job_intelligence | RT |
| Candidate match queue | top MATCHES edges | KG | RT |
| Salary benchmark | p50 role×country | salaries agg | D |
| Employer hiring trend | POSTED.count_90d | snapshots | D |
AI: "best candidates for job", "why this match".

## Agency / Consultant
| Widget | Calc | Source |
|---|---|---|
| Hot accounts to pitch | employers ↑hiring + active licence | trends | 
| Sponsor pipeline by route | licences × route | GOV join |
| Placement funnel | applications→interview→offer | app data |

## Immigration / Visa
| Widget | Calc | Source | AI |
|---|---|---|---|
| Verified sponsor search | register join | GOV | Visa Advisor |
| Route eligibility by occupation | route×occupation map | REF | advisor |
| Processing-time & acceptance | country stats | GOV/API | predict |
| Client visa-readiness | docs vs requirements | candidate | checklist |

## Candidate
| Widget | Calc | Source |
|---|---|---|
| Jobs for you (match%) | recommender #1 | KG |
| Countries for you | recommender #4 | rollups |
| Visa probability per job | job_intelligence | GOV join |
| Skill gaps to unlock sponsors | demand gap | market |

## Sponsor (employer self-service)
| Widget | Calc |
|---|---|
| Your licence status & routes | GOV |
| Your open roles reach | jobs stats |
| Talent pool matching your roles | candidates |

## Government / Regulator (aggregate, privacy-safe)
| Widget | Calc |
|---|---|
| Shortage occupations heatmap | demand vs supply |
| Sponsor compliance trend | licence status changes |
| Nationality demand flows | aggregate only |

## Analytics / Operations
| Widget | Calc | Source |
|---|---|---|
| Scraper health (pass/fail/latency) | per-source run stats | events |
| Data freshness by source | last_seen | snapshots |
| Dedup/quality rate | resolver stats | events |
| AI cost & cache hit-rate | model calls | telemetry |

**Every widget declares its data source; no widget is allowed without one (see
Phase I matrix).**
