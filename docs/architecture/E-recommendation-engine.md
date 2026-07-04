# Phase E — Recommendation Engine Design

Deterministic-first, evidence-backed (reuse `recommendation_engine` + `feature_store`
patterns). Every recommender: **Inputs → Rules/Scoring(weights) → Output + Evidence
+ Confidence → Fallback**. AI only personalizes wording, never invents facts.

## Shared scoring contract
`score = Σ(wᵢ·featureᵢ)` clamped 0..1; `confidence = f(data completeness, source
reliability)`; `evidence = [{feature, value, source, ref}]`. Fallback = deterministic
heuristic when a signal/LLM is missing (never empty).

## Recommenders

### 1. Jobs → Candidate ("jobs for you")
- **Inputs:** candidate skills/seniority/prefs (country, salary, visa need); job features.
- **Scoring:** skill overlap (w.35) + seniority fit (.15) + geo/remote (.15) + salary fit (.15) + **visa-verified (.20)**.
- **Output:** ranked jobs + match% + "why". **Evidence:** matched skills, verified sponsor licence.
- **Fallback:** norm_title + country match. **Confidence:** from profile completeness.

### 2. Candidates → Recruiter ("best candidates for this job")
- **Inputs:** job requirement vector; candidate pool. **Scoring:** inverse of #1 + resume/ATS score.
- **Output:** shortlist + gaps. **Evidence:** skills present/missing. **Fallback:** keyword match.

### 3. Sponsors → Candidate ("companies that can sponsor you")
- **Inputs:** candidate nationality + occupation + target country.
- **Scoring:** licence active (.4) + route matches occupation (.3) + recent hiring (.2) + salary threshold (.1).
- **Output:** employers ranked by sponsorship likelihood + open roles. **Evidence:** register rows.
- **This is the flagship enterprise recommender** (pure gov+scraped data).

### 4. Countries ("where should you go")
- **Inputs:** occupation, nationality, salary expectation.
- **Scoring:** shortage-occupation (.3) + acceptance rate (.2) + salary/tax net (.2) + processing time (.15) + policy openness (.15).
- **Output:** ranked countries + net-income + time-to-visa. **Fallback:** demand tables.

### 5. Salary ("what you should earn / offer")
- **Inputs:** role×country×seniority benchmark from `salaries` aggregate.
- **Output:** p25/p50/p75 + take-home. **Evidence:** N samples, freshness. **Fallback:** country median.

### 6. Occupations / upskilling
- **Inputs:** candidate skills vs in-demand skills (job market gap).
- **Output:** adjacent occupations + missing skills to unlock more sponsors. **Evidence:** demand counts.

### 7. Documents / visa readiness
- **Inputs:** target route requirements vs candidate documents.
- **Output:** checklist + gaps + expected approval. **Rules:** route requirement table. **Confidence:** completeness.

### 8. Employers → Recruiter/Agency ("hot accounts")
- **Inputs:** hiring trend, licence status, growth. **Output:** accounts to pitch + why. **Evidence:** trend series.

## Governance
- Weights are **config** (per tenant/service) — not hardcoded (reuse
  `qualification_profiles.json` pattern).
- Every recommendation logs a `RecommendationMade` event with evidence (auditable).
- Cold-start fallback everywhere → never a blank result.
