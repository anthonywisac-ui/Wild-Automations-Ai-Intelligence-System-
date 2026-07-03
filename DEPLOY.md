# Deploy → GitHub → Railway → Browser

This app is container-ready. Railway builds the `Dockerfile` (Python 3.12 +
Chromium), runs `python test_ui.py`, and gives you a public URL you open in a
browser.

## 1. Push to GitHub
```bash
# from E:\WildAutomations_Core (already a git repo)
git checkout master
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<you>/wildautomations.git
git push -u origin master
```
Secrets are safe: `.env` is gitignored (only `.env.example` is committed).

## 2. Create the Railway service
1. https://railway.app → **New Project → Deploy from GitHub repo** → pick the repo.
2. Railway detects `Dockerfile` and `railway.json` automatically and builds.
3. First build takes a few minutes (installs Chromium).

## 3. Set environment variables (Railway → Variables)
From `.env.example`, add the ones you use:
| Variable | Needed for |
|----------|-----------|
| `OPENAI_API_KEY` / `GROQ_API_KEY` | AI analysis / lead explanations |
| `AI_PROVIDER` | which LLM provider |
| `SUPABASE_URL`, `SUPABASE_KEY` | persistence (optional) |
| `APIFY_API_KEY` | Apify lead scrapers (optional) |
| `LINKEDIN_LI_AT` | authenticated LinkedIn (optional) |
Do **not** set `PORT` — Railway injects it; `test_ui.py` reads it automatically.

## 4. Open in browser
Railway → **Settings → Networking → Generate Domain** → you get
`https://<app>.up.railway.app`. Open it → the CRM dashboard loads.
Useful routes: `/api/analyze`, `/api/leads/export?format=json`,
`/api/qualification/audit`, `/api/crm/insights`.

---

## Important notes (read before relying on it)

**Resources.** Chromium is RAM-heavy. Use a Railway plan with **≥1–2 GB RAM** or
the browser scrapers will OOM. The HTTP scrapers (Jobs/University/Visa/Cars) are
light and fine on any plan.

**Datacenter IPs & Google.** Railway's IPs are datacenter IPs. Google/Instagram
CAPTCHA these **more** than home IPs, so the browser-based lead scrapers
(Maps/IG/LinkedIn-via-Google) may return little on Railway. The **reliable value
on Railway** is the HTTP/API scrapers + the qualification/enrichment/scoring
pipeline. For high-volume social leads, use a residential-proxy or an API.

**SQLite is ephemeral.** `data/*.sqlite3` (collected leads, features, events)
**resets on every redeploy**. To keep data:
- Railway → **Add Volume**, mount path `/app/data`, **or**
- migrate the stores to **Railway Postgres** (ask me — the store modules are
  isolated and easy to point at Postgres).

**Browser-less option.** If you only want the reliable HTTP scrapers, delete the
`playwright install` line from the `Dockerfile` and remove `playwright` from
`requirements.txt` → much smaller/faster image, lower RAM.
