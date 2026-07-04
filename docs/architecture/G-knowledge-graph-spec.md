# Phase G — Knowledge Graph Specification

Materialized from the ER model (projection over `events`). Storage: start with
Postgres adjacency (`knowledge_nodes`, `knowledge_edges`) + recursive CTEs; move
to a native graph (Neo4j/AGE) only if traversal cost demands. Reuse
`evidence_graph` node/edge substrate.

## Node types (attributes)
| Node | Key attributes |
|---|---|
| Country | iso, region, currency, avg_tax, employment_trend |
| City | name, country_iso, geo |
| Employer | canonical_name, industry, size, growth, risk |
| SponsorLicence | licence_name, tier, status, first_seen |
| VisaRoute | code, category, threshold_salary |
| Job | title, seniority, salary_usd, posted_at, ai_score |
| Skill | name, demand_index |
| Industry | name, growth |
| Candidate | nationality, seniority, skills_vec |
| Occupation | code (SOC), group |

## Edge types (typed, weighted, evidenced)
| Edge | From→To | Properties |
|---|---|---|
| LOCATED_IN | Employer→City | since |
| IN | City→Country | — |
| HOLDS | Employer→SponsorLicence | first_seen |
| GRANTS | SponsorLicence→VisaRoute | tier |
| SPONSORED_VIA | Job→VisaRoute | probability, evidence[] |
| POSTED | Employer→Job | count_90d, trend |
| REQUIRES | Job→Skill | weight |
| OFFERS | Job→Salary | usd |
| HAS | Candidate→Skill | level |
| MATCHES | Candidate→Job | score, confidence |
| VALID_FOR | VisaRoute→Country | — |
| SIMILAR_TO | Employer→Employer / Job→Job | cosine |

## Traversals (enterprise queries)
- **Verified sponsors for a role in a city:** `City ←LOCATED_IN← Employer →HOLDS→ Licence →GRANTS→ Route` filtered by route+status.
- **Candidate path to visa:** `Candidate →HAS→ Skill ←REQUIRES← Job ←POSTED← Employer →HOLDS→ Licence →GRANTS→ Route →VALID_FOR→ Country`.
- **Account expansion:** `Employer →SIMILAR_TO→ Employer` with hiring-trend filter.

## Graph algorithms & roadmap
| Algorithm | Use |
|---|---|
| Shortest path | candidate → nearest visa-viable job/employer |
| PageRank / centrality | most influential sponsors per industry/city (ranking) |
| Community detection (Louvain) | employer clusters, skill clusters, market segments |
| Node similarity (cosine on embeddings) | "companies/jobs like this" |
| Link prediction | **predict future sponsorship / hiring** (edge probability) |
| Graph embeddings (node2vec/GraphSAGE) | features for AI matching + recommendations |

## Future AI opportunities
- Predict which non-sponsor employers are likely to *become* sponsors (link
  prediction on HOLDS edges + hiring trend).
- Market-gap detection: occupations with high demand but few licensed sponsors.
- Nationality-flow intelligence for governments/agencies (aggregate, privacy-safe).

## Governance
Graph is a **read projection** — rebuildable from events; never a second source of
truth. Every edge carries `evidence[]` so AI can cite the exact path.
