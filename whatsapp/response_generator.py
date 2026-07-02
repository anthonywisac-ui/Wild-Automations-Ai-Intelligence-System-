"""
WhatsApp Response Generator — formats search results and other replies.
Documented in: docs/WHATSAPP AI ARCHITECTURE.md § 2.4

Usage:
    from whatsapp.response_generator import ResponseGenerator
    gen = ResponseGenerator()
    response = await gen.generate_search_response(user_id, query, results, intent)
    # {"text": "...", "type": "text", "buttons": [...], "metadata": {...}}
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResponseGenerator:
    def __init__(self) -> None:
        pass

    # ──────────────────────────────────────────────────────────────────────────
    # Public: per-intent response builders
    # ──────────────────────────────────────────────────────────────────────────

    async def generate_search_response(
        self,
        user_id: str,
        query: str,
        results: List[Dict[str, Any]],
        intent: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not results:
            return {
                "text": self._no_results_msg(query),
                "type": "text",
                "buttons": [
                    {"label": "Modify Search", "action": "modify_search"},
                    {"label": "Clear Filters", "action": "clear_filters"},
                ],
            }

        top = results[:5]
        return {
            "text": self._format_results(top, results),
            "type": "text",
            "buttons": self._search_buttons(results),
            "metadata": {"total_count": len(results), "query": query},
        }

    async def generate_filter_response(
        self,
        user_id: str,
        filters: Dict[str, Any],
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not results:
            return {
                "text": f"I applied your filters but couldn't find any matches. Try adjusting your criteria.",
                "type": "text",
                "buttons": [
                    {"label": "Clear Filters", "action": "clear_filters"},
                    {"label": "Modify Filters", "action": "modify_filters"},
                ],
            }

        msg = "✅ Filters applied! Here are your matches:\n\n"
        msg += self._format_results(results[:5], results)
        return {
            "text": msg,
            "type": "text",
            "buttons": [
                {"label": "Save Search", "action": "save_search"},
                {"label": "Clear Filters", "action": "clear_filters"},
                {"label": "More Results", "action": "more_results"},
            ],
        }

    async def generate_help_response(self) -> Dict[str, Any]:
        text = (
            "\U0001f916 *WildAutomations Help*\n\n"
            "Commands:\n"
            "• find [job/property/car] in [city]\n"
            "• filter by [salary/price/year]\n"
            "• save [ID] — bookmark a result\n"
            "• my saves — view saved items\n"
            "• notify me — set up alerts\n"
            "• daily summary — get daily digest\n\n"
            "Example: *find marketing jobs in Dubai*"
        )
        return {"text": text, "type": "text", "buttons": []}

    async def generate_save_response(self, title: str, item_id: str) -> Dict[str, Any]:
        text = (
            "✅ Saved!\n\n"
            f"*{title}* has been bookmarked.\n"
            "Reply *my saves* to view all saved opportunities."
        )
        return {"text": text, "type": "text", "buttons": [{"label": "View Saves", "action": "my_saves"}]}

    async def generate_error_response(self) -> Dict[str, Any]:
        return {
            "text": "⚠️ Something went wrong. Please try again or type *help* for options.",
            "type": "text",
            "buttons": [{"label": "Help", "action": "help"}],
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Internal formatters
    # ──────────────────────────────────────────────────────────────────────────

    def _format_results(self, top: List[Dict], all_results: List[Dict]) -> str:
        if not top:
            return "I couldn't find any opportunities matching your criteria."

        msg = "\U0001f50d Here's what I found:\n\n"
        for i, r in enumerate(top, 1):
            msg += f"{i}. *{r.get('title', 'Untitled')}*\n"
            domain = r.get("domain") or r.get("source_portal", "")

            if "job" in domain.lower():
                company = r.get("company") or r.get("company_name", "")
                if isinstance(company, dict):
                    company = company.get("name", "")
                msg += f"   Company: {company or 'Unknown'}\n"
                loc = r.get("location", "")
                if isinstance(loc, dict):
                    loc = loc.get("country") or loc.get("city") or ""
                msg += f"   Location: {loc or 'Unknown'}\n"
                sal = r.get("salary") or r.get("price", "")
                if sal:
                    msg += f"   Salary: {sal}\n"
                if r.get("visa_sponsorship"):
                    msg += "   ✅ Visa Sponsorship\n"

            elif "real_estate" in domain.lower() or "property" in domain.lower():
                msg += f"   Type: {r.get('property_type', 'N/A')}\n"
                loc = r.get("location", "")
                if isinstance(loc, dict):
                    loc = loc.get("city") or loc.get("country") or ""
                msg += f"   Location: {loc or 'N/A'}\n"
                msg += f"   Price: {r.get('price', 'N/A')} {r.get('currency', '')}\n"

            else:
                msg += f"   {r.get('description', '')[:80]}\n"

            score = r.get("match_score", 0)
            if score:
                msg += f"   Match: {int(float(score) * 100) if float(score) <= 1 else int(score)}%\n"
            msg += "\n"

        if len(all_results) > 5:
            msg += f"✨ *And {len(all_results) - 5} more results available*\n"
            msg += "   Use filters to narrow down.\n\n"

        msg += "Reply *save [ID]* to bookmark, or *filter by* to narrow results."
        return msg

    def _search_buttons(self, results: List[Dict]) -> List[Dict[str, str]]:
        buttons = []
        if results:
            domain = results[0].get("domain", "")
            if "job" in str(domain).lower():
                buttons.append({"label": "Filter by Salary", "action": "filter_salary"})
            elif "real" in str(domain).lower():
                buttons.append({"label": "Filter by Price", "action": "filter_price"})
            buttons.append({"label": "Filter by Location", "action": "filter_location"})
        buttons.append({"label": "Save This Search", "action": "save_search"})
        return buttons[:3]

    def _no_results_msg(self, query: str) -> str:
        return (
            f"I couldn't find any opportunities matching '{query}'. \U0001f605\n\n"
            "Suggestions:\n"
            "• Try different keywords\n"
            "• Broaden your search criteria\n"
            "• Check if you have filters applied\n\n"
            "What would you like to try next?"
        )
