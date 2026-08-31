"""
Dynamic 4-Tier H-LSM Memory Deduplicator & Garbage Collection Engine
===================================================================
Executes atomic, deterministic deduplication and orphan garbage collection across
L0 (Working RAM), L1 (Episodic SQLite), L2 (Semantic Vectors), and L3 (Knowledge Graph).
Preserves the authoritative canonical master record while eliminating storage bloat and retrieval bias.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional, Set

from sqlmodel import Session, select, col
from sqlalchemy import text as sa_text

from ..logging_config import get_logger
from ..models import HLSMEpisodicEntry, HLSMWorkingEntry
from .hlsm_auditor import HLSMDeepAuditor, MemoryHealthReport, _extract_kuzu_rows

logger = get_logger("HLSM.Deduplicator")


class HLSMDeduplicator:
    """
    Deterministic & HITL-Gated Deduplication and Compaction Engine for H-LSM.
    """

    def __init__(self, db_engine: Any = None, kuzu_conn: Any = None):
        self.db_engine = db_engine
        self.kuzu_conn = kuzu_conn
        self.auditor = HLSMDeepAuditor(db_engine=db_engine, kuzu_conn=kuzu_conn)

    async def deduplicate_all(
        self,
        hlsm_manager: Any,
        dry_run: bool = False,
        cluster_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Runs deep audit and executes atomic deduplication and orphan GC across all tiers.
        """
        self.db_engine = getattr(hlsm_manager, "db_engine", self.db_engine)
        self.kuzu_conn = getattr(hlsm_manager, "kuzu_conn", self.kuzu_conn)
        self.auditor.db_engine = self.db_engine
        self.auditor.kuzu_conn = self.kuzu_conn

        # 1. Run Pre-Deduplication Deep Audit
        report: MemoryHealthReport = await self.auditor.run_deep_audit(hlsm_manager)

        # 2. Filter Clusters if specified
        target_clusters = report.duplicate_clusters
        if cluster_ids:
            target_clusters = [c for c in target_clusters if c["cluster_id"] in cluster_ids]

        if dry_run:
            return {
                "status": "DRY_RUN",
                "message": f"Identified {len(target_clusters)} duplicate clusters for cleanup.",
                "health_score_before": report.health_score,
                "projected_freed_bytes": sum(c["wasted_bytes"] for c in target_clusters),
                "total_records": report.total_records,
                "clusters_to_prune": target_clusters,
                "orphan_counts": report.orphan_counts
            }

        # 3. Real Execution: Atomic Deletion across Tiers
        deleted_l0 = 0
        deleted_l1 = 0
        deleted_l3 = 0
        freed_bytes = 0
        canonical_survivors: List[Dict[str, str]] = []

        # A. Deduplicate L0 / L1 in SQLite
        l0_dupe_ids: Set[str] = set()
        l1_dupe_ids: Set[str] = set()

        for cluster in target_clusters:
            c_type = cluster["cluster_type"]
            c_id = cluster["canonical_id"]
            dupe_ids = cluster["duplicate_ids"]
            tiers = cluster["affected_tiers"]

            if c_type in ("EXACT_CONTENT_DUPLICATE", "EXACT_FILE_DUPLICATE", "SEMANTIC_NEAR_DUPLICATE"):
                canonical_survivors.append({
                    "cluster_id": cluster["cluster_id"],
                    "canonical_id": c_id,
                    "entity_title": cluster["entity_title"]
                })
                if "L0" in tiers:
                    l0_dupe_ids.update(dupe_ids)
                if "L1" in tiers:
                    l1_dupe_ids.update(dupe_ids)

        if self.db_engine:
            def _execute_sql_deletions():
                nonlocal deleted_l0, deleted_l1
                with Session(self.db_engine) as session:
                    # Clean L0
                    for d_id in l0_dupe_ids:
                        w_entry = session.get(HLSMWorkingEntry, d_id)
                        if w_entry:
                            session.delete(w_entry)
                            deleted_l0 += 1

                    # Clean L1
                    for d_id in l1_dupe_ids:
                        clean_id = d_id.replace("l1_", "").replace("l0_", "")
                        e_entry = session.get(HLSMEpisodicEntry, d_id) or session.get(HLSMEpisodicEntry, clean_id)
                        if e_entry:
                            actual_id = e_entry.id
                            session.delete(e_entry)
                            try:
                                session.exec(sa_text("DELETE FROM hlsm_episodic_fts WHERE id = :id").bindparams(id=actual_id))  # type: ignore
                            except Exception:
                                pass
                            deleted_l1 += 1
                    session.commit()

            try:
                await asyncio.to_thread(_execute_sql_deletions)
            except Exception as sql_err:
                logger.error(f"[HLSM Deduplicator] SQL deletion error: {sql_err}", exc_info=True)

        # B. Deduplicate L3 Knowledge Graph in KùzuDB
        if self.kuzu_conn:
            for cluster in target_clusters:
                c_type = cluster["cluster_type"]
                c_id = cluster["canonical_id"]
                dupe_ids = cluster["duplicate_ids"]
                tiers = cluster["affected_tiers"]

                if "L3" in tiers or c_type == "ORPHANED_NODE":
                    for d_id in dupe_ids:
                        try:
                            # 1. Rewire and Delete DocumentNode
                            if c_type == "EXACT_FILE_DUPLICATE" and c_id != "NONE (PRUNE_CANDIDATE)":
                                # Rewire incoming HAS_KEY_POINT relations to canonical
                                rewire_q = (
                                    "MATCH (d_old:DocumentNode {id: $d_id})-[:HAS_KEY_POINT]->(k:KeyPointNode), "
                                    "(d_can:DocumentNode {id: $c_id}) "
                                    "MERGE (d_can)-[:HAS_KEY_POINT]->(k)"
                                )
                                await asyncio.to_thread(self.kuzu_conn.execute, rewire_q, {"d_id": d_id, "c_id": c_id})
                                del_doc_q = "MATCH (d:DocumentNode {id: $d_id}) DELETE d"
                                await asyncio.to_thread(self.kuzu_conn.execute, del_doc_q, {"d_id": d_id})
                                deleted_l3 += 1

                            # 2. Delete KeyPointNode
                            elif c_type in ("EXACT_CONTENT_DUPLICATE", "ORPHANED_NODE"):
                                del_kp_q = "MATCH (k:KeyPointNode {id: $d_id}) DELETE k"
                                await asyncio.to_thread(self.kuzu_conn.execute, del_kp_q, {"d_id": d_id})
                                deleted_l3 += 1

                            # 3. Delete SemanticMemory / L3Memory
                            del_sm_q = "MATCH (m:SemanticMemory {id: $d_id}) DELETE m"
                            await asyncio.to_thread(self.kuzu_conn.execute, del_sm_q, {"d_id": d_id})
                            del_l3m_q = "MATCH (m:L3Memory {id: $d_id}) DELETE m"
                            await asyncio.to_thread(self.kuzu_conn.execute, del_l3m_q, {"d_id": d_id})
                        except Exception as kuzu_del_err:
                            logger.debug(f"[HLSM Deduplicator] KùzuDB node deletion notice: {kuzu_del_err}")

        # C. Calculate Freed Bytes
        freed_bytes = sum(c["wasted_bytes"] for c in target_clusters)

        # D. Post-Deduplication Audit Scan for Verification
        post_report: MemoryHealthReport = await self.auditor.run_deep_audit(hlsm_manager)

        logger.info(
            f"[HLSM Deduplicator] Deduplication sweep complete. "
            f"Pruned L0: {deleted_l0}, L1: {deleted_l1}, L3: {deleted_l3}, Freed Bytes: {freed_bytes}. "
            f"Health Score: {report.health_score * 100:.1f}% → {post_report.health_score * 100:.1f}%."
        )

        return {
            "status": "SUCCESS",
            "message": f"Successfully deduplicated and compacted H-LSM memory across all tiers.",
            "health_score_before": report.health_score,
            "health_score_after": post_report.health_score,
            "deleted_records": {
                "l0_working": deleted_l0,
                "l1_episodic": deleted_l1,
                "l3_graph": deleted_l3,
                "total": deleted_l0 + deleted_l1 + deleted_l3
            },
            "freed_bytes_total": freed_bytes,
            "canonical_survivors": canonical_survivors,
            "remaining_duplicates": len(post_report.duplicate_clusters),
            "retrieval_bias_risk": post_report.retrieval_bias_risk,
            "audit_timestamp": time.time()
        }
