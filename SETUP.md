# Wild Automations - Production Setup Guide

## Prerequisites

- **Python 3.10+** (check with `python --version` or `python3 --version`)
- **pip** (usually comes with Python)
- **git** (for cloning if needed later, but not for this initial setup)

## 1. Clone or Navigate to Project

```bash
cd E:\WildAutomations_Core
```

## 2. Run Setup Script

### Windows (PowerShell)

```powershell
.\setup.ps1
```

If you get a permission error, enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup.ps1
```

To skip browser installation (if you already have Playwright browsers):
```powershell
.\setup.ps1 -SkipBrowsers
```

### Linux / macOS (Bash)

```bash
bash setup.sh
```

The setup script will:
1. ✅ Check Python is installed
2. ✅ Create a virtual environment (venv)
3. ✅ Install all pip dependencies from `requirements.txt`
4. ✅ Install Playwright browsers (Chromium)

## 3. Activate Virtual Environment

### Windows (PowerShell)
```powershell
.\venv\Scripts\Activate.ps1
```

### Linux / macOS (Bash)
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

## 4. Configure Environment Variables

Copy `.env.example` to `.env`:

### Windows (PowerShell)
```powershell
Copy-Item .env.example .env
# Edit .env in your editor
notepad .env
```

### Linux / macOS (Bash)
```bash
cp .env.example .env
# Edit .env in your editor
nano .env
# or
vim .env
```

**Minimum required for dry-run:**
- `NOTIFY_TO` — a valid phone number (e.g., `+971501234567`) or leave empty for test mode

**For production (optional for now):**
- `SUPABASE_URL` and `SUPABASE_KEY` — Supabase database
- `OPENAI_API_KEY` — OpenAI API access
- `WHAPI_API_KEY` or `META_PHONE_NUMBER_ID + META_ACCESS_TOKEN` — WhatsApp delivery
- `TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER` — SMS delivery

## 5. Dry-Run Test

Run the orchestrator in DRY_RUN mode (validates config, crawls portals, skips delivery):

### Windows (Command Prompt or PowerShell)
```cmd
dry_run.bat
```

Or manually:
```cmd
set DRY_RUN=true
python main.py
```

### Linux / macOS (Bash)
```bash
bash dry_run.sh
```

Or manually:
```bash
DRY_RUN=true python main.py
```

**Expected output:**
```
[INFO] Manifest validated | crawlable_bots=... skipped_bots=...
[WARNING] Skipping portal bot=... portal=... reason=...
[INFO] Starting orchestration | bots=8 crawlable_bots=... dry_run=true
[INFO] crawl_bot complete bot=... portal=... pages=... items=... duplicates=...
[INFO] Portal stats: {...}
[INFO] DRY_RUN=true: stopping before delivery stage.
[INFO] Orchestration complete
```

**Note:** Since `Bayut` and `Dubizzle Cars` have placeholder selectors, expect `items_extracted=0` and `failures_by_reason={'no_items_extracted': N}`. This is expected and **not an error**.

## 6. Production Checklist

Before running live:

- [ ] **Verify selectors**: Use live DOM inspection (browser DevTools) to confirm `portal_configs` selectors for each portal
- [ ] **Add missing portals**: If you want to crawl portals beyond Bayut/Dubizzle Cars, add their config to `config/bot_manifests.py.py`
- [ ] **Set credentials**: Fill in `.env` with real Supabase, OpenAI, and WhatsApp/Twilio tokens
- [ ] **Test one bot end-to-end**: Run with `DRY_RUN=false` on a single test portal
- [ ] **Monitor logs**: Check `LOG_LEVEL=INFO` output for any acquisition/extraction failures

## 7. Run Production

Once verified and configured:

### Windows
```cmd
python main.py
```

### Linux / macOS
```bash
python main.py
```

## 8. Dependencies Overview

All dependencies are installed via `pip install -r requirements.txt`:

| Package | Purpose |
|---------|---------|
| `playwright` | Browser automation (render JS-heavy pages) |
| `crawl4ai` | Deep crawling & structured extraction (optional) |
| `scrapling` | Stealthy browser-like fetching (optional) |
| `httpx` | Async HTTP client for static page fetching |
| `openai` | OpenAI API client for LLM processing |
| `supabase` | Supabase client for database persistence |
| `selectolax` | Fast CSS selector extraction (alternative to BeautifulSoup) |
| `beautifulsoup4` | HTML parsing (fallback if selectolax unavailable) |

**Note:** If any package is not installed, the orchestrator will gracefully skip that feature:
- No `playwright` → BrowserStrategy raises an error (but HttpStrategy still works)
- No `crawl4ai` → DeepCrawlStrategy falls back to lightweight BFS pagination
- No `scrapling` → StealthStrategy falls back to BrowserStrategy

## 9. Troubleshooting

### `playwright install chromium` fails
```bash
# Manual browser install
python -m playwright install chromium
```

### `ModuleNotFoundError: No module named '...'`
```bash
# Reinstall requirements
pip install --upgrade -r requirements.txt
```

### Port/permission issues on Linux
```bash
# If port 11434 (Ollama) conflicts, disable Ollama or use a different port
# If /tmp permission denied, set TMPDIR:
export TMPDIR=/home/user/tmp
```

### Scraper hanging or timing out
- Increase `MAX_PIPELINE_RETRIES` (default 3)
- Adjust `delay_range` in portal_configs
- Check `RESPECT_ROBOTS=false` if robots.txt is blocking crawls

## 10. Next Steps

1. **Inspect live portals**: Use your browser's DevTools (F12) to identify real selectors
2. **Update portal_configs**: Edit `config/bot_manifests.py.py` with verified selectors
3. **Run dry-run again**: Confirm crawls extract items (items_extracted > 0)
4. **Deploy**: Push to Railway or your hosting platform

---

**Questions?** Check `docs/` directory or read the code comments in `core/scraper_engine.py` and `main.py`.
