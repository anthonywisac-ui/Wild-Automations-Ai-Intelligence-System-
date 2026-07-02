# Wild Automations - Quick Start (5 minutes)

## 1. Setup (2 minutes)

### Windows PowerShell
```powershell
.\setup.ps1
.\venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

### Linux / macOS Bash
```bash
bash setup.sh
source venv/bin/activate
cp .env.example .env
```

## 2. Configure (1 minute)

Edit `.env`:
```bash
# Minimum: just set a phone number or leave empty
NOTIFY_TO=+971501234567
DRY_RUN=false  # or true for testing
```

## 3. Verify (1 minute)

```bash
python verify_deps.py
```

Expected: `✓ All REQUIRED dependencies installed.`

## 4. Test (1 minute)

### Windows
```cmd
set DRY_RUN=true && python main.py
```

### Linux / macOS
```bash
DRY_RUN=true python main.py
```

Expected output:
```
[INFO] Manifest validated | crawlable_bots=2 ...
[INFO] Orchestration complete
```

## 5. Run Live (when ready)

```bash
python main.py
```

---

## Commands Cheat Sheet

| Task | Command |
|------|---------|
| Install everything | `.\setup.ps1` (Windows) or `bash setup.sh` (Linux/macOS) |
| Activate venv | `.\venv\Scripts\Activate.ps1` or `source venv/bin/activate` |
| Verify deps | `python verify_deps.py` |
| Dry-run test | `DRY_RUN=true python main.py` or `dry_run.bat` / `bash dry_run.sh` |
| Production run | `python main.py` |
| Check Python | `python --version` |
| Reinstall deps | `pip install -r requirements.txt --upgrade` |

---

## What Gets Deployed

- `main.py` — async orchestrator (load manifest → validate → crawl → score → dedupe → AI → deliver)
- `core/` — six engines (scraper, dedupe, scoring, ai, delivery, database)
- `config/bot_manifests.py.py` — bot definitions + portal configs
- `.env` — credentials (not in git)
- `requirements.txt` — pip dependencies

## What Happens on `python main.py`

1. Load manifest from `config/bot_manifests.py.py`
2. Validate each bot's portal_configs (skip if invalid)
3. **Crawl**: For each valid (bot, portal) pair, fetch pages, extract items, dedupe
4. **Process**: Score items, check deduplication, store in Supabase
5. **AI**: Send to LLM (OpenAI/Ollama) for structured processing
6. **Deliver**: Send WhatsApp/SMS alerts via Whapi/Meta/Twilio
7. **Skip if**: `DRY_RUN=true` (stops after crawl, no delivery)

---

## Troubleshooting

**"ModuleNotFoundError"**
```bash
pip install -r requirements.txt
```

**"playwright install failed"**
```bash
python -m playwright install chromium
```

**"No items extracted"**
- Selectors in `portal_configs` are placeholders. Verify against live site DOM.
- Expected when first running with example configs.

**"Navigation to this domain is not allowed"**
- Only relevant during live DOM inspection, not for production.

---

**Full docs:** See `SETUP.md` for detailed instructions and troubleshooting.
