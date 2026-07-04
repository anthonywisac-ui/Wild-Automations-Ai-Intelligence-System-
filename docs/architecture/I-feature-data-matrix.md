# Phase I — Feature ↔ Data Matrix

Rule: **no feature ships without a data source.** Each feature maps to
Entities · Tables · Scrapers · APIs · AI · Events · Notifications · Dashboard ·
Permissions. ✓ = present today, ○ = to build, — = n/a.

| Feature | Entities | Tables | Scrapers | AI | Events | Notify | Dashboard | Perm |
|---|---|---|---|---|---|---|---|---|
| **Aggregated jobs table** | Job, Employer | jobs, employers | jobspy/ats/gulftalent/uk ✓ | — | RawJobScraped ○ | — | Recruiter | jobs.read |
| **Visa-Verified badge** | Job, SponsorLicence, VisaRoute | jobs, sponsor_licences, visa_routes | uk_jobs ✓ | — | JobSponsorLinked ○ | — | Immigration, Candidate | jobs.read |
| **Employer profile** | Employer, Branch, CompanyIntel | employers, branches | ats/jobspy ✓ + enrich ○ | Company Intel ○ | EmployerEnriched ○ | — | Recruiter, Agency | employer.read |
| **Sponsor search** | SponsorLicence | sponsor_licences | uk_jobs ✓ | — | — | — | Immigration, Sponsor | sponsor.read |
| **Hiring trend / prediction** | Job, JobSnapshot | job_snapshots | scheduler ○ | Predictions ○ | TrendComputed ○ | digest | CEO, Recruiter | analytics.read |
| **Salary benchmark** | Salary, Job | salaries | reuse `_extract_salary_usd` ✓ | expected_salary ○ | — | — | Recruiter, Candidate | jobs.read |
| **Job↔Candidate match** | Candidate, Job, Skill | matches, candidate_skills | — | Matching ○ | MatchFound ○ | alert | Candidate, Recruiter | match.read |
| **Global/semantic search** | Job, Employer, Sponsor | + embeddings | — | AI Search ○ | — | — | all | search |
| **AI Visa Advisor** | SponsorLicence, VisaRoute, Job | + KG | uk_jobs ✓ | Visa Advisor ○ | — | — | Immigration, Candidate | ai.chat |
| **AI Chat (grounded)** | all | read models + KG | — | AI Chat ✓(partial) | — | — | all | ai.chat |
| **WhatsApp subscriptions** | Subscription, WhatsAppSub, Alert | subscriptions | — | — | SubscriptionTriggered ○ | WhatsApp ✓(delivery) | Candidate, Recruiter | notify.manage |
| **Enterprise export** | Job, Employer, Sponsor | read models | — | — | — | — | Analytics | export |
| **Dashboards (8)** | rollups | read models | — | varies | projections ○ | — | per role | dash.* |
| **Multi-tenant + RBAC** | Tenant, User, Role, Permission | tenants,users,roles | — | — | Auth events | — | — | admin |
| **API keys / webhooks** | APIKey, Webhook, Integration | — | — | — | — | webhook | Ops | integrations.manage |

**Reading the matrix:** the fastest enterprise value = features whose scrapers are
already ✓ and only need ○ events/joins — i.e. **Visa-Verified badge** and
**Aggregated jobs** (data exists today; only the join + projection are new). These
are P0. Features needing the **scheduler** (trend/prediction) are P1. Candidate
side is P2.
