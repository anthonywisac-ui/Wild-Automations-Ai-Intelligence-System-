# WildAutomations CRM — Integration Guide for a New AI Lead Agent

> Hand this document to whoever (human or AI) builds the new **AI Lead Agent**
> (LinkedIn / social scraping + criteria matching). It describes exactly how the
> CRM works today, what already exists, and the **hard rules** for plugging in a
> new agent **without breaking anything**.

---

## 1. What this system is

A scraper-driven intelligence CRM. It runs a set of **scrapers** across 4
categories (Jobs, University, Visa, Automobiles), then a **post-processing
pipeline** dedupes, persists, scores, AI-enriches, and profile-matches every
record. A dark-theme FastAPI dashboard (`test_ui.py`, port **8001**) shows live
results and an **AI Analyzer** view.

### Runtime entry point
- **`test_ui.py`** — the running app. Launch: `python test_ui.py` → `http://localhost:8001`.
- There is also a larger `app.py`/`main.py` orchestrator (WhatsApp bot, admin) — **the dashboard does NOT use it**; do not wire the new agent there unless asked.

---

## 2. Data flow (how a record travels)

```
 SCRAPERS (19 registered in test_ui.py)
     │  each: async fetch_xxx(config) -> List[record dict]
     ▼
 _run_one(scraper)            # test_ui.py — runs one scraper, 45s timeout, catches errors
     ▼
 _collect_all_records()       # test_ui.py — runs ALL scrapers, flattens, tags _category/_source
     ▼
 DataPipeline.process()       # core/pipeline.py — THE BRAIN
     ├─ 1. dedupe   (core/dedupe_engine.py)   url+title identity
     ├─ 2. persist  (core/store.py)           SQLite (+ Supabase mirror) + 30d history
     ├─ 3. score    (core/ai_analyzer.py)     appeal + deal Z-score using history baselines
     ├─ 4. ai_enrich(core/llm_client.py)      GROQ/Gemini/Mistral/Cerebras/Ollama one-liner
     └─ 5. match    (matching/profile_matcher.py) + delivery (best-effort)
     ▼
 /api/analyze  → JSON {summary, records[], stages{}}  → AI Analyzer UI
```

The plain scraper cards (Run All / per-category) come from **SSE** endpoints
(`/api/stream`, `/api/stream/category/{cat}`, `/api/run/{idx}`) — these bypass the
pipeline and show raw scraper output. The **AI Analyzer** tab uses the pipeline.

---

## 3. What already exists (reuse — do NOT rebuild)

### 3.1 Registered scrapers (19) — in `test_ui.py` `SCRAPERS = [...]`
| Category | Scrapers | Live source |
|----------|----------|-------------|
| Jobs (4) | Indeed/Muse, GulfTalent·Remotive, Greenhouse·WWR·RemoteOK, UK Sponsored | The Muse+Arbeitnow, Remotive, ATS APIs, gov.uk |
| University (8) | HIPO ×2, THE, QS, College Scorecard, Admissions, Global Admissions ×2, News RSS | hipo.ac, data.gov, RSS |
| Visa (5) | US Bulletin, Canada PR, Visa Index, Passport (Henley), EU Schengen | gov sites, GitHub CSV, EU API |
| Automobiles (2) | NHTSA Toyota, NHTSA BMW | NHTSA VPIC + fueleconomy.gov (real specs, no prices) |

### 3.2 Core engine modules (all wired into the pipeline)
- `core/dedupe_engine.py` — `DedupEngine.is_duplicate(url, content, title)` / `add_record(...)`
- `core/store.py` — `get_store()` → `save_batch(records)`, `load_recent(days, category)`, `count()`. SQLite primary + Supabase mirror.
- `core/ai_analyzer.py` — `analyze_records(records, history=None)`, `summarize(scored)`. Heuristic value scoring (Leniency, ROI, Net Purchasing Power, Visa Probability, Deal Z-score).
- `core/llm_client.py` — `get_llm()` → `LLMClient.complete(prompt, ...)`. Auto-detects provider from env keys.
- `core/pipeline.py` — `get_pipeline()` → `DataPipeline.process(records, profiles=None, do_match=True, do_deliver=False)`.
- `matching/profile_matcher.py` — `ProfileMatcher.match_opportunity(profile, opportunity, domain)` → `{overall_score, dimensions}`. Domains: `jobs`, `vehicles`, `real_estate`, general.
- `delivery/notification_delivery.py` — `NotificationDelivery.deliver(notification)` (WhatsApp/email/web; best-effort).

### 3.3 Available credentials (in `.env`)
- **Supabase**: `SUPABASE_URL`, `SUPABASE_KEY` (set). Run `migrations/crm_records.sql` once to enable the mirror.
- **LLM**: `GROQ_API_KEY` (active). Client also supports `GEMINI_API_KEY`, `MISTRAL_API_KEY`, `CEREBRAS_API_KEY`, `OLLAMA_HOST` — add any and it auto-activates (priority: groq→cerebras→gemini→mistral→openai→ollama).
- Not set: WhatsApp/Twilio (delivery runs in log/queue mode).

### 3.4 Python dependencies (already installed in `.venv`)
`fastapi`, `uvicorn`, `httpx`, `python-dotenv`, `supabase`, `beautifulsoup4`,
`selectolax`, `python-jobspy` (unused on Windows — OpenSSL crash), `feedparser`,
`rapidfuzz` (optional). **Prefer `httpx` for HTTP scraping** — it works reliably
here with `verify=False`.

---

## 4. THE CONTRACT — how to add the new AI Lead Agent (do this exactly)

The new agent is just **another scraper** that returns records in the standard
schema. The pipeline then dedupes/scores/enriches/matches it automatically — you
get all the CRM power for free by conforming to the contract.

### 4.1 Create the client module
Put it at `core/lead_agent_client.py` (or `agents/lead_agent.py`). It MUST expose
one async function:

```python
async def fetch_leads(portal_config: dict) -> list[dict]:
    params = portal_config.get("lead_params") or {}
    # ... scrape LinkedIn/social, apply criteria ...
    return [ _to_record(x) for x in results ]   # list of standard record dicts
```

### 4.2 Return the STANDARD record schema (mandatory)
Every record dict MUST have these keys (missing → it still works but scores worse):

```python
{
  "title":       str,          # headline (person name + role, or lead title)
  "source_url":  str,          # UNIQUE per lead (LinkedIn profile/post URL). CRITICAL:
                               # must be unique per record or dedupe merges them.
  "description": str,          # summary text used by NLP scoring + LLM enrich
  "location":    str,          # city/country — used by matching + tax/COL scoring
  "price":       str,          # salary/value if any, else ""
  "metadata": {
      "type":       "lead",    # NEW type — see 4.4
      "source":     "linkedin_live" | "<your_source>",   # never contains "fallback" if live
      "scraped_at": "<iso8601 UTC>",
      # ... any extra fields (company, headline, connections, skills, match_reason) ...
  }
}
```

### 4.3 Register it in `test_ui.py` `SCRAPERS`
Add ONE dict to the list (copy an existing entry's shape):

```python
{
    "name": "LinkedIn Lead Agent",
    "bot": "AI Lead Engine",
    "emoji": "🧲",
    "category": "Leads",          # NEW category (see 4.5)
    "mode": "AI Agent",
    "module": "core.lead_agent_client",
    "fn": "fetch_leads",
    "config": {
        "portal_name": "LinkedIn Leads", "crawl_mode": "lead_agent",
        "lead_params": {"keywords": "...", "criteria": {...}, "results_wanted": 10},
    },
},
```
`_run_one` will dynamically `__import__` the module and call `fn(config)` with a
45s timeout — no other wiring needed for it to appear on the dashboard.

### 4.4 (Optional but recommended) Teach the scorer about leads
If you want Universal-Appeal scoring tuned for leads, add a branch in
`core/ai_analyzer.py`:
- In `_category_of()` map `metadata.type == "lead"` → `"Leads"`.
- In `analyze_records()` add `elif cat == "Leads": scores = _score_lead(r)`.
- Write `_score_lead(r)` returning the same shape as `_score_job` (universal_appeal_score, value_rating, deal_breakdown).
If you skip this, leads fall through to `_score_generic` (freshness-based) — still safe.

### 4.5 (Optional) Add "Leads" to matching + UI
- `core/pipeline.py` `_DOMAIN_MAP`: add `"Leads": "jobs"` (reuse job matching) or "general".
- `_page_new.py`: add a sidebar nav button + an `azFilterSet('Leads',...)` chip (copy the Jobs button). Then re-splice (see §6).

---

## 5. HARD RULES — do not break these

1. **Never modify existing scraper clients' function signatures.** They are
   `async def fetch_xxx(portal_config: dict) -> list[dict]`. Keep that exact shape.
2. **Always give each record a UNIQUE `source_url`.** Dedup identity is
   `source_url + title`. Same URL for many records → they get merged/lost.
3. **Never let an exception escape your fetch function.** Wrap network calls in
   `try/except`, return a **fallback list** on failure (like other clients do).
   The pipeline and `_run_one` also guard you, but fail soft yourself.
4. **Every network call uses `httpx.AsyncClient(timeout=..., verify=False)`.**
   Do NOT use `python-jobspy` / `curl_cffi` on Windows (OpenSSL crash). If a
   library crashes the process, isolate it in a subprocess (see `jobspy_client.py`).
5. **Respect the 45s per-scraper budget.** Keep total calls bounded; use
   `asyncio.gather` for concurrency, add per-call timeouts.
6. **Do not touch the SSE endpoints or existing JS logic** in `_page_new.py`.
   Add new UI as *new* elements/functions only.
7. **Secrets only from `os.getenv`.** Never hardcode keys. New provider keys go
   in `.env`; the LLM client already auto-detects them.
8. **The pipeline is the only place that scores/persists.** Your agent just
   returns clean records — do not call the DB or scorer yourself.
9. **After editing `_page_new.py`, you MUST re-splice into `test_ui.py`** (§6),
   because `_PAGE()` lives inside `test_ui.py` at runtime.
10. **LinkedIn scraping is fragile & rate-limited/ToS-sensitive.** Prefer an
    official/partner API or an authorized data source; add backoff + a static
    fallback so the dashboard never breaks when the source blocks you.

---

## 6. Build / test loop (exact commands)

```bash
# 1. syntax-check any core module you add/edit
.venv/Scripts/python.exe -c "import py_compile; py_compile.compile('core/lead_agent_client.py', doraise=True)"

# 2. if you edited _page_new.py, re-splice _PAGE() into test_ui.py, then syntax-check
#    (use the existing splice script pattern: find `def _PAGE(`, replace to next top-level def)
.venv/Scripts/python.exe -c "import py_compile; py_compile.compile('test_ui.py', doraise=True)"

# 3. test the new client in isolation BEFORE touching the server
#    (assert it returns list[dict] with unique source_urls and metadata.type)

# 4. restart server & verify no regression + new agent live
#    kill python, start test_ui.py, then:
#    GET /api/run/<new_index>       -> your agent's raw output
#    GET /api/analyze?refresh=true  -> pipeline stages + your leads scored/enriched
```

**Definition of done:** `/api/run/<idx>` returns your live leads; `/api/analyze`
`stages.dedupe/persist/score/ai_enrich/match` all `active`; existing 19 scrapers
still return `status: ok`; server does not crash on `Run All`.

---

## 7. Where to drop your files

```
WildAutomations_Core/
├── core/lead_agent_client.py     ← your scraper/agent logic (NEW)
├── test_ui.py                    ← add 1 entry to SCRAPERS (+ optional analyzer branch)
├── _page_new.py                  ← optional: new sidebar tab/filter, then RE-SPLICE
├── .env                          ← add LINKEDIN_* / provider keys if needed
└── docs/INTEGRATION GUIDE — NEW AI AGENT.md   ← this file
```

Keep the agent self-contained in its own module. It plugs into the existing
brain by contract, so the CRM stays sustainable and nothing else has to change.
