"""
Notification Templates — WhatsApp + Email message formatters.
Documented in: docs/NOTIFICATION ENGINE.md § 3.2

Usage:
    from delivery.templates import NotificationTemplates
    t = NotificationTemplates()
    msg = t.render("whatsapp", "opportunity_alert", {
        "title": "Senior Dev", "location": "Dubai", "match_score": 87,
        "salary": "AED 25k/mo", "description": "...", "id": "abc123",
        "domain": "jobs", "date": "2026-06-30",
    })
"""

from typing import Any, Dict


class NotificationTemplates:
    """
    Template store for all notification channels.
    render() does simple {key} substitution — no Jinja2 required.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, Dict[str, str]] = {

            # ── WhatsApp ──────────────────────────────────────────────────────
            "whatsapp": {

                "opportunity_alert": (
                    "🔔 *New Opportunity Alert!*\n\n"
                    "📌 {title}\n"
                    "🌍 {location}\n"
                    "📊 Match Score: {match_score}%\n"
                    "{salary_line}"
                    "\n"
                    "{description}\n"
                    "\n"
                    "Domain: {domain}\n"
                    "Reply *view {id}* for details\n"
                    "Reply *save {id}* to bookmark\n"
                    "Reply *notify me* for similar"
                ),

                "daily_summary": (
                    "📊 *Daily Summary — {date}*\n\n"
                    "Total Opportunities: {total}\n"
                    "New Today: {new}\n"
                    "Match Rate: {match_rate}%\n\n"
                    "Top Matches:\n"
                    "{top_opportunities}\n\n"
                    "Reply *help* to see options"
                ),

                "save_confirm": (
                    "✅ Saved!\n\n"
                    "*{title}* has been added to your saved list.\n"
                    "Reply *my saves* to view all saved opportunities."
                ),

                "no_results": (
                    "🔍 No results found for *{query}*\n\n"
                    "Suggestions:\n"
                    "{suggestions}\n\n"
                    "Try a broader search or different keywords."
                ),

                "help": (
                    "🤖 *WildAutomations Help*\n\n"
                    "Commands:\n"
                    "• find [job/property/car] in [city]\n"
                    "• filter by [salary/price/year]\n"
                    "• save [ID] — bookmark a result\n"
                    "• my saves — view saved items\n"
                    "• notify me — set up alerts\n"
                    "• daily summary — get daily digest\n\n"
                    "Example: *find marketing jobs in Dubai*"
                ),

                "error": (
                    "⚠️ Something went wrong while processing your request.\n"
                    "Please try again or type *help* for options."
                ),
            },

            # ── Email (HTML) ──────────────────────────────────────────────────
            "email": {

                "opportunity_alert": """<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white; }}
  .header {{ background: #1a237e; color: white; padding: 20px; }}
  .content {{ padding: 20px; }}
  .card {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 4px; }}
  .badge {{ background: #4caf50; color: white; padding: 2px 10px; border-radius: 3px; font-size: 12px; }}
  .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
  a.btn {{ background: #1a237e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header"><h2>🔔 New Opportunity Alert</h2></div>
  <div class="content">
    <p>Hi {user_name},</p>
    <p>We found a new opportunity matching your preferences!</p>
    <div class="card">
      <h3>{title}</h3>
      <p><strong>Domain:</strong> {domain}</p>
      <p><strong>Location:</strong> {location}</p>
      <p><strong>Match Score:</strong> <span class="badge">{match_score}%</span></p>
      {salary_html}
      <p>{description}</p>
      <br>
      <a class="btn" href="{url}">View Details</a>
    </div>
    <p>Best regards,<br>WildAutomations Team</p>
  </div>
  <div class="footer">
    <p>You're receiving this because you subscribed to notifications.</p>
    <p><a href="{unsubscribe_url}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>""",

                "daily_summary": """<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white; }}
  .header {{ background: #1a237e; color: white; padding: 20px; }}
  .content {{ padding: 20px; }}
  .stats {{ background: #f0f4ff; padding: 15px; border-radius: 4px; display: flex; gap: 30px; }}
  .stat {{ text-align: center; }}
  .stat-num {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
  .card {{ border: 1px solid #ddd; padding: 12px; margin: 8px 0; border-radius: 4px; }}
  .footer {{ text-align: center; padding: 20px; color: #888; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header"><h2>📊 Daily Summary</h2></div>
  <div class="content">
    <p>Hi {user_name},</p>
    <div class="stats">
      <div class="stat"><div class="stat-num">{total}</div><div>Total</div></div>
      <div class="stat"><div class="stat-num">{new}</div><div>New Today</div></div>
      <div class="stat"><div class="stat-num">{match_rate}%</div><div>Match Rate</div></div>
    </div>
    <h3>Top Opportunities</h3>
    {top_opportunities_html}
    <p>Best regards,<br>WildAutomations Team</p>
  </div>
  <div class="footer">
    <p><a href="{unsubscribe_url}">Unsubscribe</a></p>
  </div>
</div>
</body>
</html>""",
            },
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def render(self, channel: str, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render template with context dict.
        Missing keys are left as-is (no KeyError raised).
        """
        ch = self._templates.get(channel, {})
        template = ch.get(template_name)
        if not template:
            raise ValueError(f"NotificationTemplates: no template '{channel}/{template_name}'")

        # Safe substitution — missing keys kept as literal {key}
        result = template
        for k, v in context.items():
            result = result.replace("{" + k + "}", str(v))
        return result

    def render_whatsapp_alert(self, item: Dict[str, Any]) -> str:
        """Convenience: build WhatsApp opportunity_alert from a ScrapedItem-like dict."""
        salary = item.get("price") or item.get("salary") or ""
        salary_line = f"💰 {salary}\n" if salary else ""
        desc = (item.get("description") or item.get("raw_text") or "")[:200]
        return self.render("whatsapp", "opportunity_alert", {
            "title": item.get("title") or "Opportunity",
            "location": item.get("location") or "N/A",
            "match_score": item.get("match_score", "—"),
            "salary_line": salary_line,
            "description": desc,
            "domain": item.get("source_portal", "general"),
            "id": item.get("id") or item.get("source_url", "")[-8:],
        })

    def add_template(self, channel: str, name: str, template: str) -> None:
        self._templates.setdefault(channel, {})[name] = template

    def list_templates(self) -> Dict[str, list]:
        return {ch: list(tpls.keys()) for ch, tpls in self._templates.items()}
