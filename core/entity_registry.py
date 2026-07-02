"""
Canonical Entity Registry — Wave 3.

Merges entities resolved from different sources (Google, Maps, LinkedIn,
Facebook, Instagram, …) into a SINGLE canonical entity keyed by canonical_id.
Builds a relationship graph (Company → Branch / Reviews / Jobs / Complaints /
Opportunities / Technologies / Contacts).

Used per pipeline run (in-memory), history-aware via the record batch. Merges
are additive: sources are unioned, confidence takes the max, evidence pooled.
Framework-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.domain import (EntityType, EvidenceNode, RelationType, Relationship,
                         ResolvedEntity)

logger = logging.getLogger(__name__)

# entity_type → the relationship a child has toward its parent Company
_CHILD_REL = {
    EntityType.BRANCH: RelationType.BRANCH,
    EntityType.JOB: RelationType.JOB,
    EntityType.REVIEW: RelationType.REVIEW,
    EntityType.COMPLAINT: RelationType.COMPLAINT,
    EntityType.OPPORTUNITY: RelationType.OPPORTUNITY,
    EntityType.LEAD: RelationType.CONTACT,
    EntityType.PERSON: RelationType.EMPLOYEE,
}


class CanonicalRegistry:
    def __init__(self) -> None:
        self._entities: Dict[str, ResolvedEntity] = {}

    # ── registration / merge ─────────────────────────────────────────────────
    def register(self, entity: ResolvedEntity) -> ResolvedEntity:
        """Merge `entity` into the canonical store; return the canonical entity."""
        cid = entity.canonical_id
        existing = self._entities.get(cid)
        if existing is None:
            self._entities[cid] = entity
            self._ensure_parent(entity)
            return entity

        # merge: union sources, max confidence, pool evidence, keep best name
        for s in entity.sources:
            if s and s not in existing.sources:
                existing.sources.append(s)
        if entity.confidence > existing.confidence:
            existing.confidence = entity.confidence
        existing.source_reliability = max(existing.source_reliability, entity.source_reliability)
        if len(entity.name) > len(existing.name):
            existing.name = entity.name
        existing.evidence.extend(entity.evidence)
        if entity.parent_id and not existing.parent_id:
            existing.parent_id = entity.parent_id
        self._ensure_parent(existing)
        return existing

    def _ensure_parent(self, child: ResolvedEntity) -> None:
        """Create a Company stub for a child's parent + wire the relationship edges."""
        if not child.parent_id:
            return
        parent = self._entities.get(child.parent_id)
        if parent is None:
            parent = ResolvedEntity(
                canonical_id=child.parent_id, entity_type=EntityType.COMPANY,
                name=child.name, reasoning="synthesized parent company")
            self._entities[child.parent_id] = parent
        rel = _CHILD_REL.get(child.entity_type, RelationType.BRANCH)
        if not any(r.target_id == child.canonical_id and r.rel_type == rel
                   for r in parent.relationships):
            parent.relationships.append(Relationship(rel_type=rel, target_id=child.canonical_id,
                                                     detail=child.name[:80]))
        if not any(r.rel_type == RelationType.PARENT for r in child.relationships):
            child.relationships.append(Relationship(rel_type=RelationType.PARENT,
                                                    target_id=child.parent_id))

    # ── typed edges within the batch (Job→Employer, Review→Business) ──────────
    def link_children(self) -> None:
        """Attach same-company children (by canonical name match) as typed edges."""
        by_name: Dict[str, ResolvedEntity] = {}
        for e in self._entities.values():
            if e.entity_type in (EntityType.BUSINESS, EntityType.COMPANY, EntityType.EMPLOYER):
                by_name.setdefault(e.name.lower(), e)
        for e in self._entities.values():
            if e.entity_type in _CHILD_REL and not e.parent_id:
                comp = by_name.get((e.name or "").lower())
                if comp and comp.canonical_id != e.canonical_id:
                    rel = _CHILD_REL[e.entity_type]
                    if not any(r.target_id == e.canonical_id for r in comp.relationships):
                        comp.relationships.append(Relationship(rel_type=rel,
                                                              target_id=e.canonical_id,
                                                              detail=e.name[:80]))

    # ── access ───────────────────────────────────────────────────────────────
    def get(self, canonical_id: str) -> Optional[ResolvedEntity]:
        return self._entities.get(canonical_id)

    def all(self) -> List[ResolvedEntity]:
        return list(self._entities.values())

    def persist_all(self) -> int:
        """Persist every canonical entity to the durable store (histories maintained)."""
        try:
            from core import canonical_store
        except Exception as exc:
            logger.warning("entity_registry: persistence unavailable: %s", exc)
            return 0
        count = 0
        for e in self._entities.values():
            if canonical_store.upsert(e):
                count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        multi = [e for e in self._entities.values() if len(e.sources) > 1]
        rels = sum(len(e.relationships) for e in self._entities.values())
        return {
            "canonical_entities": len(self._entities),
            "multi_source_entities": len(multi),
            "relationships": rels,
        }
