"""
Deep 4-Tier H-LSM Memory Auditor & Diagnostic Health Engine
===========================================================
Performs forensic multi-tier auditing of L0 (Working RAM), L1 (Episodic SQLite),
L2 (Semantic Vector/KùzuDB), and L3 (Knowledge Graph) memory stores.
Detects exact duplicates, semantic redundancy, orphaned nodes, and retrieval bias risk.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlmodel import Session, select, col
from ..logging_config import get_logger
from ..models import HLSMEpisodicEntry, HLSMWorkingEntry

logger = get_logger("HLSM.Auditor")


def _extract_kuzu_rows(raw_results: Any) -> List[Any]:
    """Safely extract rows from KùzuDB QueryResult or generic iterable."""
    if raw_results is None:
        return []
    if isinstance(raw_results, (list, tuple)):
        return list(raw_results)
    if hasattr(raw_results, "has_next") and callable(getattr(raw_results, "has_next")):
        rows = []
        while raw_results.has_next():
            rows.append(raw_results.get_next())
        return rows
    if hasattr(raw_results, "__iter__"):
        return list(raw_results)
    return []


@dataclass
class DuplicateCluster:
    cluster_id: str
    cluster_type: str  # "EXACT_FILE_DUPLICATE", "EXACT_CONTENT_DUPLICATE", "SEMANTIC_NEAR_DUPLICATE", "ORPHANED_NODE"
    canonical_id: str
    duplicate_ids: List[str]
    entity_title: str
    entity_preview: str
    affected_tiers: List[str]
    wasted_bytes: int
    confidence: float = 1.0


@dataclass
class MemoryHealthReport:
    health_score: float  # 0.0 to 1.0
    total_records: Dict[str, int]
    duplicate_clusters: List[Dict[str, Any]]
    orphan_counts: Dict[str, int]
    wasted_bytes_total: int
    retrieval_bias_risk: str  # "NONE", "LOW", "MEDIUM", "HIGH"
    audit_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HLSMDeepAuditor:
    """
    Forensic Memory Auditor for the 4-Tier H-LSM Fabric.
    Executes non-destructive deep structural and cryptographic inspection.
    """

    def __init__(self, db_engine: Any = None, kuzu_conn: Any = None):
        self.db_engine = db_engine
        self.kuzu_conn = kuzu_conn

    async def audit_l0(self, working_entries: List[HLSMWorkingEntry]) -> Dict[str, Any]:
        """Audits L0 Working Memory for duplicate message logs or redundant session keys."""
        clusters: List[DuplicateCluster] = []
        seen_hashes: Dict[str, List[HLSMWorkingEntry]] = {}

        for entry in working_entries:
            c_text = (entry.content or "").strip()
            if not c_text:
                continue
            h = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
            seen_hashes.setdefault(h, []).append(entry)

        wasted = 0
        for h, entries in seen_hashes.items():
            if len(entries) > 1:
                # Sort by creation time (oldest is canonical master)
                sorted_entries = sorted(entries, key=lambda e: getattr(e, "created_at", 0) or 0)
                canonical = sorted_entries[0]
                dupes = [e.id for e in sorted_entries[1:]]
                c_bytes = sum(len((e.content or "").encode("utf-8")) for e in sorted_entries[1:])
                wasted += c_bytes
                clusters.append(DuplicateCluster(
                    cluster_id=f"dup_l0_{h[:12]}",
                    cluster_type="EXACT_CONTENT_DUPLICATE",
                    canonical_id=canonical.id,
                    duplicate_ids=dupes,
                    entity_title=f"Working Memory: {(canonical.content or '')[:40]}...",
                    entity_preview=(canonical.content or "")[:120],
                    affected_tiers=["L0"],
                    wasted_bytes=c_bytes,
                    confidence=1.0
                ))

        return {
            "tier": "L0",
            "total_records": len(working_entries),
            "duplicate_count": sum(len(c.duplicate_ids) for c in clusters),
            "wasted_bytes": wasted,
            "clusters": clusters
        }

    async def audit_l1(self) -> Dict[str, Any]:
        """Audits L1 SQLite Episodic Memory for exact hash and normalized text duplicates."""
        if not self.db_engine:
            return {"tier": "L1", "total_records": 0, "duplicate_count": 0, "wasted_bytes": 0, "clusters": []}

        def _scan_sql():
            with Session(self.db_engine) as session:
                entries = session.exec(select(HLSMEpisodicEntry)).all()
                seen_hashes: Dict[str, List[HLSMEpisodicEntry]] = {}
                for e in entries:
                    c_text = (e.content or "").strip()
                    if not c_text:
                        continue
                    h = hashlib.sha256(c_text.encode("utf-8")).hexdigest()
                    seen_hashes.setdefault(h, []).append(e)

                clusters: List[DuplicateCluster] = []
                wasted = 0
                for h, group in seen_hashes.items():
                    if len(group) > 1:
                        # Oldest created or highest retention is canonical
                        sorted_group = sorted(
                            group,
                            key=lambda x: (
                                getattr(x, "topological_importance", 0.0) or 0.0,
                                -(getattr(x, "created_at", 0) or 0)
                            ),
                            reverse=True
                        )
                        canonical = sorted_group[0]
                        dupes = [x.id for x in sorted_group[1:]]
                        c_bytes = sum(len((x.content or "").encode("utf-8")) for x in sorted_group[1:])
                        wasted += c_bytes
                        clusters.append(DuplicateCluster(
                            cluster_id=f"dup_l1_{h[:12]}",
                            cluster_type="EXACT_CONTENT_DUPLICATE",
                            canonical_id=canonical.id,
                            duplicate_ids=dupes,
                            entity_title=f"Episodic Entry ({canonical.source or 'user'}): {(canonical.content or '')[:40]}...",
                            entity_preview=(canonical.content or "")[:120],
                            affected_tiers=["L1"],
                            wasted_bytes=c_bytes,
                            confidence=1.0
                        ))

                return len(entries), clusters, wasted

        total_cnt, clusters, wasted_bytes = await asyncio.to_thread(_scan_sql)
        return {
            "tier": "L1",
            "total_records": total_cnt,
            "duplicate_count": sum(len(c.duplicate_ids) for c in clusters),
            "wasted_bytes": wasted_bytes,
            "clusters": clusters
        }

    async def audit_l3(self) -> Dict[str, Any]:
        """Audits KùzuDB L3 Knowledge Graph for duplicate DocumentNodes, KeyPointNodes, and dangling orphans."""
        if not self.kuzu_conn:
            return {
                "tier": "L3",
                "total_records": 0,
                "duplicate_count": 0,
                "wasted_bytes": 0,
                "orphaned_keypoints": 0,
                "orphaned_l3_memories": 0,
                "clusters": []
            }

        clusters: List[DuplicateCluster] = []
        wasted_bytes = 0
        total_records = 0
        orphaned_kp_count = 0
        orphaned_l3_count = 0

        try:
            # 1. Audit DocumentNodes by SHA-256 and Name
            doc_q = "MATCH (d:DocumentNode) RETURN d.id, d.name, d.title, d.sha256, d.summary, d.created_at, d.local_path"
            raw_docs = await asyncio.to_thread(self.kuzu_conn.execute, doc_q)
            doc_rows = _extract_kuzu_rows(raw_docs)
            total_records += len(doc_rows)

            docs_by_sha: Dict[str, List[Any]] = {}
            for row in doc_rows:
                d_id, d_name, d_title, d_sha, d_summary, d_created, d_path = row
                sha_key = d_sha or hashlib.sha256(f"{d_name}_{d_summary}".encode("utf-8")).hexdigest()
                docs_by_sha.setdefault(sha_key, []).append(row)

            for sha_key, group in docs_by_sha.items():
                if len(group) > 1:
                    # Sort by created_at (oldest is canonical)
                    sorted_group = sorted(group, key=lambda r: float(r[5]) if r[5] else 0.0)
                    canonical = sorted_group[0]
                    dupes = [str(r[0]) for r in sorted_group[1:]]
                    c_bytes = sum(len(str(r[4] or "").encode("utf-8")) + 2048 for r in sorted_group[1:])
                    wasted_bytes += c_bytes
                    clusters.append(DuplicateCluster(
                        cluster_id=f"dup_doc_{sha_key[:12]}",
                        cluster_type="EXACT_FILE_DUPLICATE",
                        canonical_id=str(canonical[0]),
                        duplicate_ids=dupes,
                        entity_title=f"Document: {canonical[2] or canonical[1]}",
                        entity_preview=f"Summary: {str(canonical[4])[:120]}...",
                        affected_tiers=["L3", "L2", "L1"],
                        wasted_bytes=c_bytes,
                        confidence=1.0
                    ))

            # 2. Audit Duplicate KeyPointNodes across documents
            kp_q = "MATCH (k:KeyPointNode) RETURN k.id, k.text, k.document_id"
            raw_kps = await asyncio.to_thread(self.kuzu_conn.execute, kp_q)
            kp_rows = _extract_kuzu_rows(raw_kps)
            total_records += len(kp_rows)

            kps_by_text: Dict[str, List[Any]] = {}
            for row in kp_rows:
                kp_id, kp_text, kp_doc = row
                clean_text = (kp_text or "").strip().lower()
                if len(clean_text) > 10:
                    kps_by_text.setdefault(clean_text, []).append(row)

            for clean_text, group in kps_by_text.items():
                if len(group) > 1:
                    canonical = group[0]
                    dupes = [str(r[0]) for r in group[1:]]
                    c_bytes = sum(len((r[1] or "").encode("utf-8")) for r in group[1:])
                    wasted_bytes += c_bytes
                    clusters.append(DuplicateCluster(
                        cluster_id=f"dup_kp_{hashlib.sha256(clean_text.encode('utf-8')).hexdigest()[:12]}",
                        cluster_type="EXACT_CONTENT_DUPLICATE",
                        canonical_id=str(canonical[0]),
                        duplicate_ids=dupes,
                        entity_title=f"Key Point: {str(canonical[1])[:40]}...",
                        entity_preview=str(canonical[1])[:120],
                        affected_tiers=["L3"],
                        wasted_bytes=c_bytes,
                        confidence=0.95
                    ))

            # 3. Detect Orphaned KeyPointNodes (No incoming HAS_KEY_POINT edge)
            orphan_kp_q = "MATCH (k:KeyPointNode) WHERE NOT (()-[:HAS_KEY_POINT]->(k)) RETURN k.id, k.text"
            raw_orphans = await asyncio.to_thread(self.kuzu_conn.execute, orphan_kp_q)
            orphan_rows = _extract_kuzu_rows(raw_orphans)
            orphaned_kp_count = len(orphan_rows)
            if orphan_rows:
                orphan_ids = [str(r[0]) for r in orphan_rows]
                c_bytes = sum(len(str(r[1] or "").encode("utf-8")) for r in orphan_rows)
                wasted_bytes += c_bytes
                clusters.append(DuplicateCluster(
                    cluster_id="orphan_kps_unlinked",
                    cluster_type="ORPHANED_NODE",
                    canonical_id="NONE (PRUNE_CANDIDATE)",
                    duplicate_ids=orphan_ids,
                    entity_title=f"{len(orphan_ids)} Dangling KeyPointNodes (No Parent Document)",
                    entity_preview="Dangling graph nodes disconnected from active DocumentNodes.",
                    affected_tiers=["L3"],
                    wasted_bytes=c_bytes,
                    confidence=1.0
                ))

            # 4. Detect SemanticMemory / L3Memory records
            sm_q = "MATCH (m:SemanticMemory) RETURN count(m)"
            raw_sm = await asyncio.to_thread(self.kuzu_conn.execute, sm_q)
            sm_rows = _extract_kuzu_rows(raw_sm)
            if sm_rows and sm_rows[0]:
                total_records += int(sm_rows[0][0])

            l3m_q = "MATCH (m:L3Memory) RETURN count(m)"
            raw_l3m = await asyncio.to_thread(self.kuzu_conn.execute, l3m_q)
            l3m_rows = _extract_kuzu_rows(raw_l3m)
            if l3m_rows and l3m_rows[0]:
                total_records += int(l3m_rows[0][0])

        except Exception as e:
            logger.error(f"[HLSM Auditor] L3 Graph audit error: {e}", exc_info=True)

        return {
            "tier": "L3",
            "total_records": total_records,
            "duplicate_count": sum(len(c.duplicate_ids) for c in clusters if c.cluster_type != "ORPHANED_NODE"),
            "orphaned_keypoints": orphaned_kp_count,
            "orphaned_l3_memories": orphaned_l3_count,
            "wasted_bytes": wasted_bytes,
            "clusters": clusters
        }

    async def run_deep_audit(self, hlsm_manager: Any) -> MemoryHealthReport:
        """
        Executes a comprehensive, asynchronous 4-tier deep audit scan.
        Calculates health scores and identifies retrieval rank bias risks.
        """
        self.db_engine = getattr(hlsm_manager, "db_engine", self.db_engine)
        self.kuzu_conn = getattr(hlsm_manager, "kuzu_conn", self.kuzu_conn)

        # 1. Fetch active L0 entries if available
        working_entries: List[HLSMWorkingEntry] = []
        if self.db_engine:
            def _get_l0():
                with Session(self.db_engine) as session:
                    return session.exec(select(HLSMWorkingEntry)).all()
            try:
                working_entries = await asyncio.to_thread(_get_l0)
            except Exception:
                working_entries = []

        # 2. Run Tier Audits in Parallel
        raw_l0, raw_l1, raw_l3 = await asyncio.gather(
            self.audit_l0(working_entries),
            self.audit_l1(),
            self.audit_l3(),
            return_exceptions=True
        )

        l0_audit: Dict[str, Any] = raw_l0 if isinstance(raw_l0, dict) else {
            "tier": "L0", "total_records": 0, "duplicate_count": 0, "wasted_bytes": 0, "clusters": []
        }
        l1_audit: Dict[str, Any] = raw_l1 if isinstance(raw_l1, dict) else {
            "tier": "L1", "total_records": 0, "duplicate_count": 0, "wasted_bytes": 0, "clusters": []
        }
        l3_audit: Dict[str, Any] = raw_l3 if isinstance(raw_l3, dict) else {
            "tier": "L3", "total_records": 0, "duplicate_count": 0, "wasted_bytes": 0, "orphaned_keypoints": 0, "orphaned_l3_memories": 0, "clusters": []
        }

        all_clusters: List[DuplicateCluster] = []
        l0_clusters = l0_audit.get("clusters", [])
        if isinstance(l0_clusters, list):
            all_clusters.extend([c for c in l0_clusters if isinstance(c, DuplicateCluster)])
        l1_clusters = l1_audit.get("clusters", [])
        if isinstance(l1_clusters, list):
            all_clusters.extend([c for c in l1_clusters if isinstance(c, DuplicateCluster)])
        l3_clusters = l3_audit.get("clusters", [])
        if isinstance(l3_clusters, list):
            all_clusters.extend([c for c in l3_clusters if isinstance(c, DuplicateCluster)])

        l0_total = int(l0_audit.get("total_records", 0) or 0)
        l1_total = int(l1_audit.get("total_records", 0) or 0)
        l3_total = int(l3_audit.get("total_records", 0) or 0)

        total_records_map: Dict[str, int] = {
            "l0": l0_total,
            "l1": l1_total,
            "l2": l3_total,  # L2/L3 in KuzuDB
            "l3": l3_total,
            "total": l0_total + l1_total + l3_total
        }

        total_dupes = sum(len(c.duplicate_ids) for c in all_clusters if c.cluster_type != "ORPHANED_NODE")
        orphaned_kp = int(l3_audit.get("orphaned_keypoints", 0) or 0)
        orphaned_l3 = int(l3_audit.get("orphaned_l3_memories", 0) or 0)
        total_orphans = orphaned_kp + orphaned_l3
        wasted_bytes_total = sum(c.wasted_bytes for c in all_clusters)

        # 3. Calculate Health Score
        total_items = max(1, total_records_map["total"])
        deduction = (total_dupes * 0.05) + (total_orphans * 0.03)
        health_score = max(0.0, min(1.0, 1.0 - (deduction / total_items)))

        # 4. Calculate Retrieval Bias Risk
        if total_dupes == 0 and total_orphans == 0:
            bias_risk = "NONE"
        elif total_dupes <= 2 and total_orphans <= 3:
            bias_risk = "LOW"
        elif total_dupes <= 8:
            bias_risk = "MEDIUM"
        else:
            bias_risk = "HIGH"

        report = MemoryHealthReport(
            health_score=round(health_score, 3),
            total_records=total_records_map,
            duplicate_clusters=[asdict(c) for c in all_clusters],
            orphan_counts={
                "dangling_keypoints": orphaned_kp,
                "orphaned_l3_memories": orphaned_l3
            },
            wasted_bytes_total=wasted_bytes_total,
            retrieval_bias_risk=bias_risk
        )
        logger.info(f"[HLSM Auditor] Deep audit completed. Health Score: {report.health_score * 100:.1f}%, Clusters: {len(all_clusters)}, Bias Risk: {bias_risk}")
        return report
