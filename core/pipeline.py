"""
DataPipeline — the CRM "brain" that the dashboard was previously bypassing.

Wires the built architecture into one resilient flow:

    raw scraped records
        → 1. DEDUPE        (core.dedupe_engine)      remove url/content/title dupes
        → 2. PERSIST       (core.store)              save + load 30d history (baselines)
        → 3. SCORE         (core.ai_analyzer)        appeal/deal scoring w/ history
        → 4. AI ENRICH     (core.ai_processor)       optional LLM (if key) else skip
        → 5. MATCH+DELIVER (matching + delivery)     optional profile match / alerts

Every stage degrades gracefully: a missing dependency, credential, or runtime
error disables THAT stage only and is recorded in `stages`, never crashing the
pipeline. With no external creds it behaves exactly like the old dashboard plus
dedup + persistence + historical baselines (all local, all reliable).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Category → matcher domain
_DOMAIN_MAP = {"Jobs": "jobs", "Automobiles": "vehicles", "University": "general",
               "Visa": "general", "Leads": "jobs"}

# A default demo profile so matching produces visible output with zero real users.
DEFAULT_PROFILE = {
    "id": "demo",
    "name": "Demo Seeker",
    "preferred_countries": ["UAE", "United Arab Emirates", "Dubai", "Remote", "United Kingdom"],
    "salary_range": {"min": 60000, "max": 250000},
    "skills": ["software", "engineer", "python", "data", "developer", "cloud"],
    "education": {"level": "master"},
    "experience_years": 4,
    "visa_required": True,
    "budget_range": {"min": 10000, "max": 60000},
    "preferred_makes": ["Toyota", "BMW"],
}


class DataPipeline:
    def __init__(self) -> None:
        # Stage 1: dedupe (pure python, always available)
        from core.dedupe_engine import DedupEngine, DedupConfig
        self.dedupe = DedupEngine(DedupConfig(title_fuzzy_threshold=88))

        # Stage 2: persistence (local SQLite always; Supabase mirror if creds)
        from core.store import get_store
        self.store = get_store()

        # Stage 4: AI enrichment via unified multi-provider LLM client
        # (GROQ / Gemini / Mistral / Cerebras / OpenAI / Ollama — auto-detected).
        try:
            from core.llm_client import get_llm
            self._llm = get_llm()
        except Exception as exc:
            logger.warning("pipeline: llm_client unavailable: %s", exc)
            self._llm = None

        # Stage 5: matching + delivery (matching is pure; delivery best-effort)
        self._matcher = None
        self._delivery = None
        try:
            from matching.profile_matcher import ProfileMatcher
            self._matcher = ProfileMatcher()
        except Exception as exc:
            logger.warning("pipeline: matcher unavailable: %s", exc)
        try:
            from delivery.notification_delivery import NotificationDelivery
            self._delivery = NotificationDelivery()
        except Exception as exc:
            logger.warning("pipeline: delivery unavailable: %s", exc)

    # ── Stage 1 ──────────────────────────────────────────────────────────────
    def _dedupe(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dedup on the reliable unique key (source_url). Fuzzy content/title
        matching is only used for records that lack a distinct URL — otherwise
        near-identical-but-distinct listings (e.g. car trims) get wrongly merged.
        """
        self.dedupe.reset()
        unique: List[Dict[str, Any]] = []
        removed = 0
        for r in records:
            url = (r.get("source_url") or "").strip()
            title = (r.get("title") or "").strip()
            # Identity = url + title composite. This treats a listing as unique
            # by BOTH its link and its title, so distinct items that share a
            # landing page (e.g. car trims, gov register pages) are NOT merged,
            # while a genuine re-scrape of the same listing IS caught.
            identity = f"{url}||{title}" if (url or title) else (r.get("description") or "")
            is_dup, _ = self.dedupe.is_duplicate(identity, content=None, title=None)
            if is_dup:
                removed += 1
                continue
            self.dedupe.add_record(identity, content=None, title=None)
            unique.append(r)
        return unique, removed

    # ── Stage 4 ──────────────────────────────────────────────────────────────
    async def _ai_enrich(self, scored: List[Dict[str, Any]], top_n: int = 12) -> Dict[str, Any]:
        """Best-effort LLM one-liner enrichment of the top-ranked records.

        Runs concurrently with a hard timeout so a slow/failing LLM never stalls
        the pipeline. No-op (returns inactive) when no provider is configured.
        """
        if not self._llm:
            return {"active": False, "reason": "no LLM key (heuristic scoring)"}

        import asyncio
        targets = scored[:top_n]

        async def enrich_one(s: Dict[str, Any]) -> None:
            od = s["original_data"]
            a = s["ai_scores"]
            prompt = (
                f"Category: {a.get('category')}. Listing: {od.get('title','')}. "
                f"Details: {(od.get('description','') or '')[:220]}. "
                f"Our value rating: {a.get('value_rating')}. "
                "In ONE punchy sentence (max 18 words), tell a job/deal seeker why this is worth their attention."
            )
            try:
                text = await asyncio.wait_for(self._llm.complete(prompt, max_tokens=60), timeout=12)
                if text:
                    a["deal_breakdown"]["llm_summary"] = text
            except Exception:
                pass

        try:
            await asyncio.wait_for(asyncio.gather(*(enrich_one(s) for s in targets)), timeout=30)
        except Exception as exc:
            logger.warning("pipeline: AI enrich partial/timeout: %s", exc)

        enriched_n = sum(1 for s in targets if s["ai_scores"]["deal_breakdown"].get("llm_summary"))
        return {"active": enriched_n > 0, "provider": self._llm.provider,
                "model": self._llm.model, "enriched": enriched_n}

    # ── Stage 5 ──────────────────────────────────────────────────────────────
    async def _match_and_deliver(self, scored: List[Dict[str, Any]],
                                 profiles: List[Dict[str, Any]],
                                 deliver: bool) -> Dict[str, Any]:
        if not self._matcher or not profiles:
            return {"matched": 0, "delivered": 0, "active": False}
        matched = 0
        delivered = 0
        for s in scored:
            cat = s["ai_scores"].get("category", "")
            domain = _DOMAIN_MAP.get(cat, "general")
            od = s["original_data"]
            best = 0.0
            best_pid = None
            for prof in profiles:
                try:
                    m = await self._matcher.match_opportunity(prof, _to_opportunity(od, cat), domain)
                    sc = m.get("overall_score", 0.0)
                    if sc > best:
                        best, best_pid = sc, prof.get("id")
                except Exception:
                    continue
            s["ai_scores"]["match"] = {"best_score": round(best, 3), "profile_id": best_pid}
            if best >= 0.6:
                matched += 1
                if deliver and self._delivery and best >= 0.72:
                    try:
                        ok = await self._delivery.deliver({
                            "profile_id": best_pid,
                            "title": od.get("title", ""),
                            "body": s["ai_scores"]["deal_breakdown"].get("why", ""),
                            "url": od.get("source_url", ""),
                            "channels": ["web"],
                        })
                        delivered += 1 if ok else 0
                    except Exception:
                        pass
        return {"matched": matched, "delivered": delivered, "active": True}

    # ── Stage 2.35: Qualification Engine (gatekeeper, BEFORE any crawl) ────────
    def _qualify_leads(self, records: List[Dict[str, Any]], service: str = ""
                       ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Deterministically qualify each lead on pre-crawl signals, BEFORE the
        expensive enrichment crawl. Survivors are tagged with a decision + depth;
        rejected/blacklisted businesses are persisted (never dropped) and removed
        from the pipeline so no crawl is wasted on them. Non-lead records pass
        through untouched."""
        try:
            from core import qualification_engine as qe, rejection_store, ticket_segmentation
        except Exception as exc:
            return records, {"active": False, "reason": str(exc)}

        kept: List[Dict[str, Any]] = []
        rejected = 0
        by_decision: Dict[str, int] = {}
        for r in records:
            md = r.get("metadata") or {}
            if md.get("type") != "lead":
                kept.append(r)
                continue
            svc = service or md.get("_service") or md.get("service") or ""
            result = qe.qualify(r, service=svc)
            by_decision[result.decision] = by_decision.get(result.decision, 0) + 1
            # attach ticket profile for survivors + audit
            ticket_segmentation.enrich_record(r)
            md = r.setdefault("metadata", {})
            md["qualification"] = result.as_dict()
            md["qualification_score"] = result.overall
            md["qualification_depth"] = result.depth
            if result.qualified:
                kept.append(r)
            else:
                rejection_store.record(r, result.as_dict())
                rejected += 1
        total_leads = sum(by_decision.values())
        return kept, {
            "active": True, "leads_evaluated": total_leads,
            "qualified": total_leads - rejected, "rejected": rejected,
            "by_decision": by_decision,
            "crawl_reduction_pct": round(100.0 * rejected / total_leads, 1) if total_leads else 0.0,
        }

    # ── Stage 2.4: Data Enrichment (leads only) ───────────────────────────────
    async def _enrich_data(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enrich lead businesses with website/contact/tech/social/pain signals
        before entity resolution. Non-lead records are left untouched."""
        import asyncio
        try:
            from core import enrichment_engine
        except Exception as exc:
            return {"active": False, "reason": str(exc)}
        leads = [r for r in records if (r.get("metadata") or {}).get("type") == "lead"]
        if not leads:
            return {"active": False, "reason": "no leads"}
        try:
            enriched = await asyncio.wait_for(
                enrichment_engine.enrich_batch(leads, concurrency=6, per_timeout=12),
                timeout=90)
        except Exception as exc:
            logger.warning("pipeline: enrichment timeout/err: %s", exc)
            enriched = sum(1 for r in leads if (r.get("metadata") or {}).get("enriched"))
        # Ticket segmentation already ran in the Qualification stage; refresh here
        # in case enrichment revealed stronger review signals (idempotent).
        try:
            from core import ticket_segmentation
            for r in leads:
                ticket_segmentation.enrich_record(r)
        except Exception as exc:
            logger.warning("pipeline: ticket segmentation failed: %s", exc)
        with_site = sum(1 for r in leads if (r.get("metadata") or {}).get("website"))
        with_phone = sum(1 for r in leads if (r.get("metadata") or {}).get("phone"))
        cached = sum(1 for r in leads if (r.get("metadata") or {}).get("enrichment_cached"))
        changes = sum(len(((r.get("metadata") or {}).get("enrichment") or {}).get("changes") or [])
                      for r in leads)
        disc = {}
        for r in leads:
            src = (((r.get("metadata") or {}).get("enrichment") or {}).get("discovery") or {}).get("source")
            if src:
                disc[src] = disc.get(src, 0) + 1
        tickets = {}
        for r in leads:
            t = (r.get("metadata") or {}).get("ticket")
            if t:
                tickets[t] = tickets.get(t, 0) + 1
        return {"active": True, "leads": len(leads), "enriched": enriched,
                "with_website": with_site, "with_phone": with_phone,
                "from_cache": cached, "changes_detected": changes,
                "discovery_sources": disc, "ticket_mix": tickets}

    # ── Stage 2.5: buying-signal analysis for leads ──────────────────────────
    async def _analyze_leads(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run GROQ buying-signal analysis on Lead records (post text + comments).
        Attaches intent/sentiment/buying_signals/actionable to each lead's metadata
        so the scorer and matcher can use them. No-op without an LLM provider."""
        if not self._llm:
            return {"active": False, "reason": "no LLM key"}
        leads = [r for r in records if (r.get("metadata") or {}).get("type") == "lead"]
        if not leads:
            return {"active": False, "reason": "no leads"}

        import asyncio
        try:
            from plugins.scrapers_analyzer import SocialAnalyzer
            analyzer = SocialAnalyzer({})   # routes to unified LLM (GROQ) when no OpenRouter key
        except Exception as exc:
            logger.warning("pipeline: lead analyzer unavailable: %s", exc)
            return {"active": False, "reason": str(exc)}

        try:
            from core import review_miner
        except Exception:
            review_miner = None

        async def one(r: Dict[str, Any]) -> None:
            m = r["metadata"]
            platform = m.get("platform")
            # Google Maps businesses → Review Miner (operational pain hypothesis)
            if platform == "google_maps" and review_miner:
                try:
                    place = {"name": m.get("company"), "category": m.get("category"),
                             "rating": m.get("rating"), "review_count": m.get("review_count"),
                             "keyword": m.get("category")}
                    pain = await asyncio.wait_for(review_miner.mine_business(place), timeout=10)
                    m["pain_likelihood"] = pain.get("pain_likelihood")
                    m["likely_friction"] = pain.get("likely_friction")
                    m["department"] = pain.get("department")
                    m["recommended_offer"] = pain.get("recommended_offer")
                except Exception:
                    pass
                return
            # Social posts → buying-signal analysis
            text = m.get("post_text") or f"{r.get('title','')} {r.get('description','')}"
            comments = m.get("comments") or []
            if comments:
                text = f"{text}\nComments: " + " | ".join(comments[:5])
            try:
                a = await asyncio.wait_for(analyzer.analyze(text), timeout=10)
                if isinstance(a, dict):
                    m["buying_signals"] = a.get("buying_signals", []) or m.get("buying_signals", [])
                    m["sentiment"] = a.get("sentiment") or m.get("sentiment")
                    m["intent"] = a.get("intent") or m.get("intent")
                    m["actionable"] = a.get("actionable", m.get("actionable"))
            except Exception:
                pass

        try:
            await asyncio.wait_for(asyncio.gather(*(one(r) for r in leads[:15])), timeout=35)
        except Exception as exc:
            logger.warning("pipeline: lead analysis partial/timeout: %s", exc)

        analyzed = sum(1 for r in leads if (r.get("metadata") or {}).get("intent")
                       or (r.get("metadata") or {}).get("pain_likelihood") is not None)
        return {"active": analyzed > 0, "provider": self._llm.provider, "analyzed": analyzed}

    # ── Stage 2.6: domain enrichment (Admissions + Visa intelligence) ─────────
    async def _enrich_domains(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Attach academic (late-intake/stipend) + visa (friction/ease) flags via
        deterministic detection, with GROQ upgrade on the most promising records."""
        import asyncio
        try:
            from core import academic_intel, visa_intel
        except Exception as exc:
            return {"active": False, "reason": str(exc)}

        unis = [r for r in records if (r.get("metadata") or {}).get("type", "").startswith("admission")
                or (r.get("metadata") or {}).get("type") in ("university", "admissions_guide", "admissions_data")]
        visas = [r for r in records if "visa" in (r.get("metadata") or {}).get("type", "")
                 or "passport" in (r.get("metadata") or {}).get("type", "")]

        # Deterministic flags for everyone (fast); GROQ upgrade for a capped subset.
        for r in unis:
            blob = f"{r.get('title','')} {r.get('description','')}"
            r.setdefault("metadata", {})["academic_flags"] = academic_intel.flags(blob, r["metadata"])
        for r in visas:
            blob = f"{r.get('title','')} {r.get('description','')}"
            r.setdefault("metadata", {})["visa_flags"] = visa_intel.flags(blob, r["metadata"])

        if self._llm:
            async def up_uni(r):
                try:
                    r["metadata"]["academic_flags"] = await asyncio.wait_for(academic_intel.mine(r), timeout=9)
                except Exception:
                    pass

            async def up_visa(r):
                try:
                    r["metadata"]["visa_flags"] = await asyncio.wait_for(visa_intel.mine(r), timeout=9)
                except Exception:
                    pass
            try:
                await asyncio.wait_for(
                    asyncio.gather(*[up_uni(r) for r in unis[:8]] + [up_visa(r) for r in visas[:8]]),
                    timeout=30,
                )
            except Exception:
                pass

        late = sum(1 for r in unis if (r["metadata"].get("academic_flags") or {}).get("is_late_intake"))
        easy = sum(1 for r in visas if (r["metadata"].get("visa_flags") or {}).get("friction_level") == "Low")
        return {"active": True, "universities": len(unis), "visas": len(visas),
                "late_intakes": late, "easy_visas": easy}

    # ── Stage 6: self-learning (signal memory) ────────────────────────────────
    def _learn(self, scored: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Record how each (goal, query, source) performed so the Intent Planner
        prioritises winning queries next time. Runs only on Lead records that carry
        a goal + query tag."""
        try:
            from core import signal_memory
        except Exception as exc:
            return {"active": False, "reason": str(exc)}

        # group appeal scores by (goal, query, platform)
        groups: Dict[tuple, List[float]] = {}
        for s in scored:
            od = s.get("original_data") or {}
            m = od.get("metadata") or {}
            if m.get("type") != "lead" or not m.get("_goal"):
                continue
            key = (m["_goal"], m.get("_query"), m.get("platform"))
            groups.setdefault(key, []).append(s["ai_scores"]["universal_appeal_score"])

        recorded = 0
        for (goal, query, source), appeals in groups.items():
            signal_memory.record_outcome(goal, query, source, appeals)
            recorded += 1
        if not groups:
            return {"active": False, "reason": "no tagged leads"}
        # surface what's been learned for this goal
        goal = next(iter(groups))[0]
        return {"active": True, "recorded_groups": recorded, "memory": signal_memory.summary(goal)}

    # ── Stage 2.7: entity resolution + registry + evidence + dynamic confidence
    async def _resolve_entities(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve each record to a canonical entity (deterministic-first), merge
        cross-source duplicates in the registry, build the evidence graph, and
        compute the dynamic confidence. Attaches results additively to metadata."""
        try:
            from core import entity_resolver, evidence_graph, feature_store
            from core.entity_registry import CanonicalRegistry
        except Exception as exc:
            return {"active": False, "reason": str(exc)}

        registry = CanonicalRegistry()
        for r in records:
            try:
                m = r.setdefault("metadata", {})
                resolved = await entity_resolver.resolve(r, category=r.get("_category", ""))
                nodes = evidence_graph.build(r, resolved)
                resolved.evidence = nodes
                canonical = registry.register(resolved)

                # data completeness (back out from Wave 1: conf = completeness × reliability)
                w1_conf = float(m.get("confidence") or 0.5)
                rel_frac = max(0.01, (m.get("source_reliability") or 65) / 100.0)
                completeness = max(0.0, min(1.0, w1_conf / rel_frac))
                ev_strength = evidence_graph.strength(nodes)
                components = evidence_graph.confidence_components(
                    resolved.confidence, resolved.source_reliability, ev_strength, completeness)
                final_conf = evidence_graph.dynamic_confidence(
                    resolved.confidence, resolved.source_reliability, ev_strength, completeness)

                m["canonical_id"] = canonical.canonical_id
                m["entity_type"] = resolved.entity_type.value
                m["parent_id"] = resolved.parent_id
                m["entity_reasoning"] = resolved.reasoning
                m["evidence_strength"] = ev_strength
                m["confidence_components"] = components   # visible, never hidden
                m["final_confidence"] = final_conf
                m["evidence"] = [n.model_dump() for n in nodes]

                # Feature Store: compute a versioned, time-aware vector ONCE from
                # evidence; persist an append-only snapshot (point-in-time history).
                # Learning consumes only the store, never raw evidence.
                vector = feature_store.compute_vector(r, resolved)
                feature_store.persist(canonical.canonical_id, vector,
                                      trace_id=m.get("trace_id", ""))
                m["features"] = feature_store.flatten(vector)      # flat for scoring
                m["feature_vector"] = vector                        # rich for audit
            except Exception as exc:
                logger.warning("pipeline: entity resolution failed on a record: %s", exc)

        registry.link_children()
        persisted = registry.persist_all()
        self._registry = registry
        st = registry.stats()
        st["active"] = True
        st["persisted"] = persisted
        return st

    def _attach_evidence(self, scored: List[Dict[str, Any]]) -> None:
        """Surface the evidence graph + dynamic confidence in each score's breakdown."""
        for s in scored:
            m = (s.get("original_data") or {}).get("metadata") or {}
            db = s.get("ai_scores", {}).get("deal_breakdown")
            if isinstance(db, dict):
                db["evidence"] = m.get("evidence", [])
                db["evidence_strength"] = m.get("evidence_strength")
                db["confidence_components"] = m.get("confidence_components")
                db["final_confidence"] = m.get("final_confidence")
                db["canonical_id"] = m.get("canonical_id")

    # ── Stage 5.5: Recommendation Engine (decision engine) ────────────────────
    async def _recommend(self, scored: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic recommendations from the evidence graph for every record;
        LLM personalizes the pitch for the top-priority ones only."""
        try:
            from core import recommendation_engine
        except Exception as exc:
            return {"active": False, "reason": str(exc)}

        try:
            from core import event_timeline
            from core.event_timeline import EventType
        except Exception:
            event_timeline = None

        recs: List[Any] = []
        for s in scored:
            try:
                od = s.get("original_data") or {}
                rec = recommendation_engine.recommend(od)
                db = s.get("ai_scores", {}).get("deal_breakdown")
                if isinstance(db, dict):
                    db["recommendation"] = rec.model_dump()
                # Record a RECOMMENDATION event → establishes the lineage the
                # Learning Engine attributes outcomes back to (feedback loop).
                if event_timeline and rec.canonical_id:
                    m = od.get("metadata") or {}
                    event_timeline.record(
                        EventType.RECOMMENDATION, canonical_id=rec.canonical_id,
                        payload={"offer": rec.recommended_service, "channel": rec.outreach_channel,
                                 "query": m.get("_query", ""), "source": m.get("source", ""),
                                 "persona": m.get("_goal", ""), "priority": rec.priority})
                recs.append((s, rec))
            except Exception as exc:
                logger.warning("pipeline: recommend failed on a record: %s", exc)

        # LLM personalize the pitch for the top few (Hot/High), capped + concurrent
        if self._llm:
            import asyncio
            top = [(s, r) for s, r in recs if r.priority in ("Hot", "High")][:8]

            async def polish(s, r):
                try:
                    await asyncio.wait_for(
                        recommendation_engine.personalize(s.get("original_data") or {}, r), timeout=10)
                    db = s.get("ai_scores", {}).get("deal_breakdown")
                    if isinstance(db, dict):
                        db["recommendation"] = r.model_dump()
                except Exception:
                    pass
            try:
                await asyncio.wait_for(asyncio.gather(*(polish(s, r) for s, r in top)), timeout=30)
            except Exception:
                pass

        prio = {}
        for _, r in recs:
            prio[r.priority] = prio.get(r.priority, 0) + 1
        return {"active": True, "recommended": len(recs), "by_priority": prio,
                "personalized": len([1 for _, r in recs if r.priority in ("Hot", "High")][:8])}

    # ── Orchestration ────────────────────────────────────────────────────────
    async def process(self, records: List[Dict[str, Any]], *,
                      profiles: Optional[List[Dict[str, Any]]] = None,
                      do_match: bool = True, do_deliver: bool = False) -> Dict[str, Any]:
        from core import ai_analyzer

        stages: Dict[str, Any] = {}

        # 1. dedupe
        unique, removed = self._dedupe(records)
        stages["dedupe"] = {"active": True, "in": len(records), "out": len(unique), "removed": removed}

        # 2. persist + load history for baselines
        history: List[Dict[str, Any]] = []
        try:
            inserted = await self.store.save_batch(unique)
            history = await self.store.load_recent(days=30)
            total = await self.store.count()
            stages["persist"] = {"active": True, "backend": self.store.backend_name(),
                                 "new_inserted": inserted, "history_records": len(history),
                                 "total_stored": total}
        except Exception as exc:
            logger.warning("pipeline: persist failed: %s", exc)
            stages["persist"] = {"active": False, "error": str(exc)}

        # 2.35 QUALIFICATION ENGINE — the gatekeeper. Deterministically qualify
        # leads on pre-crawl signals and REJECT weak ones BEFORE any crawl runs.
        # Rejected businesses are persisted with structured reasons, never dropped.
        unique, qstats = self._qualify_leads(unique)
        stages["qualification"] = qstats

        # 2.4 DATA ENRICHMENT — collect website/contact/tech/social/SEO/pain signals
        # for QUALIFIED lead businesses only, so no crawl is wasted on weak leads.
        stages["enrichment"] = await self._enrich_data(unique)

        # 2.5 buying-signal analysis on Leads (GROQ) — feeds scoring + matching
        stages["lead_analysis"] = await self._analyze_leads(unique)

        # 2.6 domain enrichment: Admissions (late-intake/stipend) + Visa (friction/ease)
        stages["domain_intel"] = await self._enrich_domains(unique)

        # 2.7 entity resolution + canonical registry + evidence graph + dynamic confidence
        stages["entity_resolution"] = await self._resolve_entities(unique)

        # 3. score with historical baselines
        scored = ai_analyzer.analyze_records(unique, history=history)
        summary = ai_analyzer.summarize(scored)
        stages["score"] = {"active": True, "scored": len(scored),
                           "baseline_population": len([r for r in (unique + history)
                                                       if (r.get("metadata") or {}).get("type") == "vehicle"])}
        # attach evidence graph + dynamic confidence onto scored output (explainability)
        self._attach_evidence(scored)

        # 4. optional LLM enrich
        stages["ai_enrich"] = await self._ai_enrich(scored)

        # 5. optional match + deliver
        profs = profiles if profiles is not None else [DEFAULT_PROFILE]
        if do_match:
            md = await self._match_and_deliver(scored, profs, do_deliver)
            stages["match_deliver"] = md
        else:
            stages["match_deliver"] = {"active": False}

        # 5.5 Recommendation Engine (decision engine) — consumes the evidence graph
        stages["recommendation"] = await self._recommend(scored)

        # 6. self-learning: record query/source outcomes for the next run
        stages["learning"] = self._learn(scored)

        # 7. Lead Explanation — attach the evidence-backed answer set every
        # qualified lead must carry before entering the CRM (deterministic).
        stages["explanation"] = self._explain_leads(scored)

        # 8. Push FINAL qualified leads to Supabase (durable, queryable). Best-effort.
        stages["supabase_leads"] = self._push_supabase_leads(scored)

        return {"summary": summary, "records": scored, "stages": stages}

    def _push_supabase_leads(self, scored: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            from core import lead_export, supabase_leads
            rows = lead_export.rows(scored)
            pushed = supabase_leads.push_leads(rows)
            return {"active": pushed > 0, "pushed": pushed, "eligible": len(rows)}
        except Exception as exc:
            return {"active": False, "reason": str(exc)}

    def _explain_leads(self, scored: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compose the CRM answer set for each qualified lead from frozen-module
        outputs (qualification + ticket + enrichment). No LLM required."""
        try:
            from core import lead_explanation
        except Exception as exc:
            return {"active": False, "reason": str(exc)}
        n = 0
        for s in scored:
            od = s.get("original_data") or s
            md = od.get("metadata") or {}
            if md.get("type") != "lead" or not md.get("qualification"):
                continue
            expl = lead_explanation.explain(od)
            md["explanation"] = expl
            s.setdefault("explanation", expl)
            n += 1
        return {"active": True, "explained": n}


def _to_opportunity(od: Dict[str, Any], cat: str) -> Dict[str, Any]:
    """Adapt a scraped record into the matcher's opportunity shape."""
    m = od.get("metadata") or {}
    opp: Dict[str, Any] = {
        "location": od.get("location", ""),
        "title": od.get("title", ""),
        "description": od.get("description", ""),
    }
    if cat == "Jobs":
        opp["skills_required"] = [w for w in (od.get("title", "") + " " + od.get("description", "")).lower().split() if len(w) > 3][:12]
        opp["visa_sponsorship"] = any(k in (od.get("description", "") or "").lower()
                                      for k in ("visa", "sponsor", "relocation"))
        opp["salary"] = {}
    elif cat == "Automobiles":
        opp["make_model"] = f"{m.get('make','')} {m.get('model','')}"
        opp["year"] = m.get("year")
        opp["price"] = m.get("price_usd")
    return opp


_PIPELINE_SINGLETON: Optional[DataPipeline] = None


def get_pipeline() -> DataPipeline:
    global _PIPELINE_SINGLETON
    if _PIPELINE_SINGLETON is None:
        _PIPELINE_SINGLETON = DataPipeline()
    return _PIPELINE_SINGLETON
