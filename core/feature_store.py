"""
Feature Store — the single source of truth for learning, scoring, and future ML.

The Learning Engine MUST NEVER read raw entities, evidence graphs, or enrichment
blobs. It consumes ONLY the outputs of this module: versioned, normalized,
time-aware feature vectors with provenance, freshness, confidence, and labels.

That contract is enforced by shape, not convention:

    compute_vector(record, resolved)  ->  FeatureVector   (rich, per-feature cells)
    persist(canonical_id, vector, trace_id)               (append-only snapshot)
    add_label(canonical_id, name, value, observed_at)     (CRM = source of truth)
    training_set(label_name)          ->  [(features, label)]  point-in-time join

Every feature is a typed cell — never a bare float:

    FeatureValue = {
        "value":       float 0..1,       normalized signal strength
        "confidence":  float 0..1,       how sure we are of this value
        "provenance":  [{source, confidence}, ...],
        "freshness_at": ISO8601,         when the underlying data was observed
        "version":     "feat@x.y",       definition version that produced it
    }

Storage (data/crm_store.sqlite3):
    feature_vectors   append-only snapshots (point-in-time correctness)
    feature_labels    append-only outcome labels (joined only at train time)

Deterministic, fail-soft, framework-agnostic, no LLM.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DB = Path(__file__).resolve().parent.parent / "data" / "crm_store.sqlite3"
_LOCK = threading.Lock()

# Bump when the meaning/normalization of any feature changes. Stored on every
# row so a trained model always knows which definition produced its inputs.
FEATURE_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class FeatureDefinition:
    """A versioned, self-describing feature. `half_life_days` drives freshness
    decay; `sources` documents the evidence types that legitimately feed it."""
    name: str
    version: str
    half_life_days: float          # signal loses half its weight after this age
    description: str
    sources: Tuple[str, ...]       # evidence types that contribute


# ── Feature registry ──────────────────────────────────────────────────────────
# Fast-decaying signals (hiring, intent) go stale quickly; structural ones
# (digital maturity, authority) age slowly.
FEATURE_DEFINITIONS: Dict[str, FeatureDefinition] = {
    "hiring_score":       FeatureDefinition("hiring_score", "1.0", 30,
                          "Active recruiting / team growth", ("hiring",)),
    "growth_score":       FeatureDefinition("growth_score", "1.0", 60,
                          "Expansion + hiring + funding composite",
                          ("expansion", "hiring", "funding")),
    "complaint_score":    FeatureDefinition("complaint_score", "1.0", 45,
                          "Operational pain / poor reviews (buying signal)",
                          ("complaint", "poor_reviews")),
    "digital_maturity":   FeatureDefinition("digital_maturity", "1.0", 120,
                          "Website/tech sophistication (inverse of missing features)",
                          ("technology_stack", "website_missing_features")),
    "technology_score":   FeatureDefinition("technology_score", "1.0", 90,
                          "Detected marketing/analytics tech stack",
                          ("technology_stack",)),
    "funding_score":      FeatureDefinition("funding_score", "1.0", 120,
                          "Recent funding / investment", ("funding",)),
    "intent_score":       FeatureDefinition("intent_score", "1.0", 14,
                          "Explicit buying intent / asking for recommendations",
                          ("intent", "recommendation")),
    "contactability":     FeatureDefinition("contactability", "1.0", 90,
                          "Reachable via phone/whatsapp/email/website",
                          ("contactability",)),
    "authority_score":    FeatureDefinition("authority_score", "1.0", 120,
                          "Trust: ratings, reach, gov/news presence",
                          ("high_ratings", "government_data", "news")),
    "engagement_score":   FeatureDefinition("engagement_score", "1.0", 45,
                          "Social activity / community discussion",
                          ("social_activity", "community_discussion")),
    "competition_score":  FeatureDefinition("competition_score", "1.0", 180,
                          "Category crowding heuristic", ()),
}

FEATURE_NAMES: List[str] = list(FEATURE_DEFINITIONS.keys())

# evidence type → (feature, inverse?)  inverse means "presence lowers the feature"
_EVIDENCE_TO_FEATURE: Dict[str, Tuple[str, bool]] = {
    "hiring":                   ("hiring_score", False),
    "expansion":                ("growth_score", False),
    "funding":                  ("funding_score", False),
    "complaint":                ("complaint_score", False),
    "poor_reviews":             ("complaint_score", False),
    "high_ratings":             ("authority_score", False),
    "technology_stack":         ("technology_score", False),
    "social_activity":          ("engagement_score", False),
    "intent":                   ("intent_score", False),
    "recommendation":           ("intent_score", False),
    "contactability":           ("contactability", False),
    "website_missing_features": ("digital_maturity", True),   # missing → low maturity
    "government_data":          ("authority_score", False),
    "news":                     ("authority_score", False),
    "community_discussion":     ("engagement_score", False),
}


def _init() -> None:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
        # legacy flat table (kept so old rows/readers never break)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS features ("
            "canonical_id TEXT PRIMARY KEY, updated_at TEXT NOT NULL, features TEXT NOT NULL)")
        # append-only time-aware snapshots
        conn.execute(
            "CREATE TABLE IF NOT EXISTS feature_vectors ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, canonical_id TEXT NOT NULL, "
            "schema_version TEXT NOT NULL, computed_at TEXT NOT NULL, "
            "trace_id TEXT, vector TEXT NOT NULL)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fv_cid_time "
                     "ON feature_vectors(canonical_id, computed_at)")
        # append-only outcome labels (CRM = source of truth)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS feature_labels ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, canonical_id TEXT NOT NULL, "
            "label_name TEXT NOT NULL, label_value REAL NOT NULL, "
            "observed_at TEXT NOT NULL, source TEXT DEFAULT 'crm')")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fl_name_time "
                     "ON feature_labels(label_name, observed_at)")
        conn.commit()


_init()


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(ts)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _cell(value: float, confidence: float, provenance: List[Dict[str, Any]],
          freshness_at: str, version: str) -> Dict[str, Any]:
    """Construct one FeatureValue cell — the atomic unit the store guarantees."""
    return {
        "value": round(_clamp(value), 3),
        "confidence": round(_clamp(confidence), 3),
        "provenance": provenance,
        "freshness_at": freshness_at,
        "version": version,
    }


# ── Rich, versioned computation ───────────────────────────────────────────────

def compute_vector(record: Dict[str, Any], resolved: Any = None,
                   observed_at: str = "") -> Dict[str, Any]:
    """Compute a full FeatureVector (per-feature cells) from the evidence graph.

    Reads only structured evidence + light metadata — never invents signals.
    `observed_at` is the freshness anchor (defaults to enrichment last_enriched
    if present, else now)."""
    md = record.get("metadata") or {}
    nodes: List[Dict[str, Any]] = md.get("evidence") or []

    # freshness anchor: prefer real observation time from enrichment cache
    enr = md.get("enrichment") or {}
    fresh_at = observed_at or enr.get("last_enriched") or _now()

    # accumulate best contribution + its provenance per feature
    best: Dict[str, float] = {n: 0.0 for n in FEATURE_NAMES}
    prov: Dict[str, List[Dict[str, Any]]] = {n: [] for n in FEATURE_NAMES}
    conf: Dict[str, float] = {n: 0.0 for n in FEATURE_NAMES}

    for n in nodes:
        et = n.get("type")
        mapping = _EVIDENCE_TO_FEATURE.get(et)
        if not mapping:
            continue
        feature, inverse = mapping
        rel = float(n.get("source_reliability", 0.65))
        raw = float(n.get("value", 0.0)) * rel
        contribution = _clamp(1.0 - raw) if inverse else _clamp(raw)
        if contribution >= best[feature]:
            best[feature] = contribution
            conf[feature] = float(n.get("confidence") or rel)
        prov[feature].append({
            "source": n.get("source", "") or "unknown",
            "confidence": round(float(n.get("confidence") or rel), 3),
        })

    # derived / heuristic features (documented provenance so they're auditable)
    if best["technology_score"] > 0 and best["digital_maturity"] == 0.0:
        best["digital_maturity"] = _clamp(0.5 + 0.5 * best["technology_score"])
        conf["digital_maturity"] = conf["technology_score"] or 0.6
        prov["digital_maturity"].append({"source": "derived:technology", "confidence": 0.6})

    reach = md.get("followers")
    if reach:
        try:
            r = math.log10(float(str(reach).replace(",", "")) + 1) / 6
            if r > best["authority_score"]:
                best["authority_score"] = _clamp(r)
                conf["authority_score"] = 0.7
                prov["authority_score"].append({"source": "social:followers", "confidence": 0.7})
        except (ValueError, TypeError):
            pass

    cat = (md.get("category") or "").lower()
    if any(k in cat for k in ("agency", "marketing", "clinic", "restaurant")):
        best["competition_score"] = 0.6
        conf["competition_score"] = 0.4
        prov["competition_score"].append({"source": "heuristic:category", "confidence": 0.4})

    best["growth_score"] = _clamp(max(best["growth_score"],
                                      0.5 * best["hiring_score"] + 0.5 * best["funding_score"]))
    if best["growth_score"] > 0 and not prov["growth_score"]:
        prov["growth_score"].append({"source": "derived:hiring+funding", "confidence": 0.5})
        conf["growth_score"] = 0.5

    features: Dict[str, Any] = {}
    for name in FEATURE_NAMES:
        d = FEATURE_DEFINITIONS[name]
        features[name] = _cell(best[name], conf[name] or (0.5 if best[name] else 0.0),
                               prov[name], fresh_at, f"{name}@{d.version}")

    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "computed_at": _now(),
        "freshness_at": fresh_at,
        "features": features,
    }


# ── Persistence (append-only, time-aware) ─────────────────────────────────────

def persist(canonical_id: str, vector: Dict[str, Any], trace_id: str = "") -> None:
    """Append a feature-vector snapshot (never overwrites → point-in-time history)
    and mirror the flat latest view into the legacy `features` table."""
    if not canonical_id or not vector:
        return
    try:
        flat = flatten(vector)
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.execute(
                "INSERT INTO feature_vectors (canonical_id,schema_version,computed_at,"
                "trace_id,vector) VALUES (?,?,?,?,?)",
                (canonical_id, vector.get("schema_version", FEATURE_SCHEMA_VERSION),
                 vector.get("computed_at", _now()), trace_id,
                 json.dumps(vector, ensure_ascii=False)))
            conn.execute(
                "INSERT INTO features (canonical_id,updated_at,features) VALUES (?,?,?) "
                "ON CONFLICT(canonical_id) DO UPDATE SET updated_at=excluded.updated_at, "
                "features=excluded.features",
                (canonical_id, _now(), json.dumps(flat, ensure_ascii=False)))
            conn.commit()
    except Exception as exc:
        logger.warning("feature_store: persist failed: %s", exc)


def get_latest(canonical_id: str) -> Dict[str, Any]:
    """Most recent full FeatureVector for an entity."""
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            row = conn.execute(
                "SELECT vector FROM feature_vectors WHERE canonical_id=? "
                "ORDER BY computed_at DESC, id DESC LIMIT 1", (canonical_id,)).fetchone()
            return json.loads(row[0]) if row else {}
    except Exception:
        return {}


def flatten(vector: Dict[str, Any]) -> Dict[str, float]:
    """Reduce a FeatureVector to {name: value} for legacy consumers/scoring."""
    feats = vector.get("features") or {}
    return {name: round(float(cell.get("value", 0.0)), 3) for name, cell in feats.items()}


# ── Labels + point-in-time training join (the ONLY learning entry point) ──────

def add_label(canonical_id: str, label_name: str, label_value: float,
              observed_at: str = "", source: str = "crm") -> None:
    """Record an outcome label (CRM is the source of truth). Append-only."""
    if not canonical_id or not label_name:
        return
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            conn.execute(
                "INSERT INTO feature_labels (canonical_id,label_name,label_value,"
                "observed_at,source) VALUES (?,?,?,?,?)",
                (canonical_id, label_name, float(label_value),
                 observed_at or _now(), source))
            conn.commit()
    except Exception as exc:
        logger.warning("feature_store: add_label failed: %s", exc)


def _freshness_weight(freshness_at: str, half_life_days: float, as_of: datetime) -> float:
    """Exponential decay: a signal observed `half_life_days` ago counts half."""
    ts = _parse_ts(freshness_at)
    if ts is None or half_life_days <= 0:
        return 1.0
    age_days = max(0.0, (as_of - ts).total_seconds() / 86400.0)
    return float(0.5 ** (age_days / half_life_days))


def training_set(label_name: str, decay: bool = True) -> List[Dict[str, Any]]:
    """The single interface the Learning Engine may use.

    For each label, join the feature vector snapshot AT OR BEFORE the label's
    observation time (no leakage) and optionally apply freshness decay. Returns
    plain, normalized rows — never raw entities or evidence.

        [{ "canonical_id", "features": {name: value}, "confidence": {name: c},
           "label": float, "observed_at", "features_computed_at" }, ...]
    """
    rows: List[Dict[str, Any]] = []
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            labels = conn.execute(
                "SELECT canonical_id,label_value,observed_at FROM feature_labels "
                "WHERE label_name=? ORDER BY observed_at ASC", (label_name,)).fetchall()
            for cid, lval, obs in labels:
                vrow = conn.execute(
                    "SELECT vector,computed_at FROM feature_vectors "
                    "WHERE canonical_id=? AND computed_at<=? "
                    "ORDER BY computed_at DESC, id DESC LIMIT 1", (cid, obs)).fetchone()
                if not vrow:
                    continue  # no feature snapshot predates the label → skip (no leakage)
                vector = json.loads(vrow[0])
                as_of = _parse_ts(obs) or datetime.now(timezone.utc)
                feats: Dict[str, float] = {}
                confs: Dict[str, float] = {}
                for name, cell in (vector.get("features") or {}).items():
                    val = float(cell.get("value", 0.0))
                    if decay:
                        hl = FEATURE_DEFINITIONS[name].half_life_days if name in FEATURE_DEFINITIONS else 60
                        val = round(val * _freshness_weight(cell.get("freshness_at", ""), hl, as_of), 4)
                    feats[name] = val
                    confs[name] = float(cell.get("confidence", 0.0))
                rows.append({
                    "canonical_id": cid,
                    "features": feats,
                    "confidence": confs,
                    "label": float(lval),
                    "observed_at": obs,
                    "features_computed_at": vrow[1],
                })
    except Exception as exc:
        logger.warning("feature_store: training_set failed: %s", exc)
    return rows


def stats() -> Dict[str, Any]:
    try:
        with _LOCK, sqlite3.connect(str(_DB), timeout=15) as conn:
            vec = conn.execute("SELECT COUNT(*), COUNT(DISTINCT canonical_id) "
                               "FROM feature_vectors").fetchone()
            lbl = conn.execute("SELECT COUNT(*), COUNT(DISTINCT label_name) "
                               "FROM feature_labels").fetchone()
            names = [r[0] for r in conn.execute(
                "SELECT DISTINCT label_name FROM feature_labels").fetchall()]
        return {
            "schema_version": FEATURE_SCHEMA_VERSION,
            "feature_count": len(FEATURE_NAMES),
            "snapshots": vec[0], "entities": vec[1],
            "labels": lbl[0], "label_types": names,
        }
    except Exception:
        return {"schema_version": FEATURE_SCHEMA_VERSION, "feature_count": len(FEATURE_NAMES)}


# ── Backward-compatible shims (existing pipeline keeps working unchanged) ──────

def compute(record: Dict[str, Any], resolved: Any = None) -> Dict[str, float]:
    """Legacy flat interface — returns {name: value}. Prefer compute_vector."""
    return flatten(compute_vector(record, resolved))


def store(canonical_id: str, feats: Dict[str, float]) -> None:
    """Legacy flat store — wraps values into minimal cells and appends a snapshot."""
    now = _now()
    vector = {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "computed_at": now, "freshness_at": now,
        "features": {
            name: _cell(float(feats.get(name, 0.0)), 0.5, [{"source": "legacy", "confidence": 0.5}],
                        now, f"{name}@{FEATURE_DEFINITIONS[name].version}")
            for name in FEATURE_NAMES if name in feats
        },
    }
    persist(canonical_id, vector)


def get(canonical_id: str) -> Dict[str, float]:
    """Legacy flat getter — latest {name: value}."""
    return flatten(get_latest(canonical_id))
