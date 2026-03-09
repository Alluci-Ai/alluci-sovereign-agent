"""
Usage & Cost Analytics Tracker for the Polytope Sovereign OS.

Tracks per-turn token usage, per-model cost calculations, and provides
aggregation APIs for date-range queries, daily rollups, and CSV export.

Reference: Sovereign Spec Sections 4.1–4.9
"""

import csv
import io
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select, col

logger = logging.getLogger("Analytics")


class UsageTracker:
    """
    Records token usage for every LLM call and computes costs
    against a configurable pricing table.
    """

    # ── Default pricing ($ per 1M tokens) ────────────────────────────────
    # Users can override via the model_pricing DB table.
    DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
        "gemini-2.0-flash": {
            "input": 0.10, "output": 0.40, "cache_read": 0.025, "cache_write": 0.025,
        },
        "gemini-2.5-pro-preview-06-05": {
            "input": 1.25, "output": 10.00, "cache_read": 0.315, "cache_write": 0.315,
        },
        "gpt-4o": {
            "input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 1.25,
        },
        "gpt-4o-mini": {
            "input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0.075,
        },
        "claude-sonnet-4-20250514": {
            "input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75,
        },
    }

    def __init__(self, db_engine):
        self.db_engine = db_engine
        self._missing_cost_models: set = set()

    # ── Recording ─────────────────────────────────────────────────────────

    def record_turn(
        self,
        session_key: str,
        model: str,
        provider: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> Dict[str, Any]:
        """
        Record a single LLM turn's token usage and calculate cost.
        Returns the computed cost breakdown.
        """
        from .models import UsageLog

        # Look up pricing — DB first, then defaults
        pricing = self._get_pricing(model)
        if pricing is None:
            self._missing_cost_models.add(model)
            logger.warning(f"[Analytics] No pricing data for model: {model}")
            cost = 0.0
        else:
            cost = (
                (input_tokens * pricing["input"] / 1_000_000)
                + (output_tokens * pricing["output"] / 1_000_000)
                + (cache_read_tokens * pricing.get("cache_read", 0) / 1_000_000)
                + (cache_write_tokens * pricing.get("cache_write", 0) / 1_000_000)
            )

        entry = UsageLog(
            session_key=session_key,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read=cache_read_tokens,
            cache_write=cache_write_tokens,
            cost=round(cost, 8),
            timestamp=datetime.now(timezone.utc),
        )

        with Session(self.db_engine) as session:
            session.add(entry)
            session.commit()

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(cost, 8),
            "model": model,
        }

    # ── Pricing Lookup ────────────────────────────────────────────────────

    def _get_pricing(self, model: str) -> Optional[Dict[str, float]]:
        """Check DB pricing table, fallback to DEFAULT_PRICING."""
        from .models import ModelPricing

        with Session(self.db_engine) as session:
            stmt = select(ModelPricing).where(ModelPricing.model_id == model)
            row = session.exec(stmt).first()
            if row:
                return {
                    "input": row.input_price_per_1m,
                    "output": row.output_price_per_1m,
                    "cache_read": row.cache_read_price,
                    "cache_write": row.cache_write_price,
                }

        return self.DEFAULT_PRICING.get(model)

    # ── Session Aggregation ───────────────────────────────────────────────

    def get_sessions(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """
        Simplified session aggregation to prevent hangs.
        """
        from .models import UsageLog

        with Session(self.db_engine) as session:
            stmt = select(UsageLog)
            if start:
                stmt = stmt.where(col(UsageLog.timestamp) >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc))
            if end:
                end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                stmt = stmt.where(col(UsageLog.timestamp) < end_dt)

            stmt = stmt.order_by(col(UsageLog.timestamp).desc()).limit(limit + 1)
            rows = session.exec(stmt).all()

        limit_reached = len(rows) > limit
        rows = rows[:limit]

        # Aggregate by session_key
        sessions: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            s = sessions.setdefault(r.session_key, {
                "session_key": r.session_key,
                "agent": "MAIN",
                "provider": r.provider,
                "channel": "System Gateway",
                "total_input": 0, "total_output": 0, "total_cost": 0.0,
                "total_cache_read": 0, "total_cache_write": 0,
                "messages": 0, "tools": 0, "errors": 0, "duration": 0,
                "turn_count": 0, "models": set(), "first_turn": None, "last_turn": None,
            })
            s["total_input"] += r.input_tokens
            s["total_output"] += r.output_tokens
            s["total_cache_read"] += r.cache_read
            s["total_cache_write"] += r.cache_write
            s["total_cost"] += r.cost
            s["turn_count"] += 1
            s["messages"] += 2 # Rough estimate: 2 messages per usage turn if we don't join with MessageLog
            s["models"].add(r.model)
            ts_str = r.timestamp.isoformat() if r.timestamp else None
            if ts_str:
                if s["first_turn"] is None or ts_str < s["first_turn"]:
                    s["first_turn"] = ts_str
                if s["last_turn"] is None or ts_str > s["last_turn"]:
                    s["last_turn"] = ts_str
            
            # Simple duration estimation (seconds between first and last turn)
            if s["first_turn"] and s["last_turn"]:
                try:
                    t1 = datetime.fromisoformat(s["first_turn"])
                    t2 = datetime.fromisoformat(s["last_turn"])
                    s["duration"] = int((t2 - t1).total_seconds())
                except:
                    pass

        session_list = []
        for s in sessions.values():
            s["models"] = list(s["models"])
            s["total_cost"] = round(s["total_cost"], 6)
            session_list.append(s)

        return {
            "sessions": session_list,
            "totals": {
                "total_input": sum(s["total_input"] for s in session_list),
                "total_output": sum(s["total_output"] for s in session_list),
                "cache_read": sum(s["total_cache_read"] for s in session_list),
                "cache_write": sum(s["total_cache_write"] for s in session_list),
                "total_cost": round(sum(s["total_cost"] for s in session_list), 6),
                "session_count": len(session_list),
            },
            "limit_reached": limit_reached,
            "missing_cost_entries": len(self._missing_cost_models),
        }

    def get_summary(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Returns high-level aggregate usage stats.
        """
        from .models import UsageLog

        with Session(self.db_engine) as session:
            stmt = select(UsageLog)
            if start:
                stmt = stmt.where(col(UsageLog.timestamp) >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc))
            if end:
                end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                stmt = stmt.where(col(UsageLog.timestamp) < end_dt)
            rows = session.exec(stmt).all()

        total_input = 0
        total_output = 0
        total_cache_read = 0
        total_cache_write = 0
        total_cost = 0.0
        unique_sessions = set()

        for r in rows:
            total_input += r.input_tokens
            total_output += r.output_tokens
            total_cache_read += r.cache_read
            total_cache_write += r.cache_write
            total_cost += r.cost
            unique_sessions.add(r.session_key)

        return {
            "total_input": total_input,
            "total_output": total_output,
            "cache_read": total_cache_read,
            "cache_write": total_cache_write,
            "total_cost": round(total_cost, 6),
            "session_count": len(unique_sessions),
        }

    # ── Daily Rollup ──────────────────────────────────────────────────────

    def get_daily(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns per-day token/cost breakdown for chart rendering.
        Sovereign Spec Section 4.4
        """
        from .models import UsageLog

        with Session(self.db_engine) as session:
            stmt = select(UsageLog)
            if start:
                stmt = stmt.where(col(UsageLog.timestamp) >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc))
            if end:
                end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
                stmt = stmt.where(col(UsageLog.timestamp) < end_dt)
            rows = session.exec(stmt).all()

        daily: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            day_key = r.timestamp.date().isoformat() if r.timestamp else "unknown"
            d = daily.setdefault(day_key, {
                "date": day_key, "input_tokens": 0, "output_tokens": 0,
                "cache_read": 0, "cache_write": 0,
                "cost": 0.0, "turns": 0,
            })
            d["input_tokens"] += r.input_tokens
            d["output_tokens"] += r.output_tokens
            d["cache_read"] += r.cache_read
            d["cache_write"] += r.cache_write
            d["cost"] += r.cost
            d["turns"] += 1

        result = sorted(daily.values(), key=lambda x: x["date"])
        for d in result:
            d["cost"] = round(d["cost"], 6)
        return result

    # ── Per-Session Timeseries ────────────────────────────────────────────

    def get_session_timeseries(self, session_key: str) -> List[Dict[str, Any]]:
        """
        Per-turn time series for a selected session.
        Sovereign Spec Section 4.5
        """
        from .models import UsageLog

        with Session(self.db_engine) as session:
            stmt = (
                select(UsageLog)
                .where(UsageLog.session_key == session_key)
                .order_by(col(UsageLog.timestamp).asc())
            )
            rows = session.exec(stmt).all()

        cumulative_cost = 0.0
        cumulative_tokens = 0
        series = []
        for r in rows:
            cumulative_cost += r.cost
            cumulative_tokens += r.input_tokens + r.output_tokens
            series.append({
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "turn_cost": round(r.cost, 8),
                "cumulative_cost": round(cumulative_cost, 6),
                "cumulative_tokens": cumulative_tokens,
            })
        return series

    # ── Session Log Retrieval ─────────────────────────────────────────────

    def get_session_log(self, session_key: str, role_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return the conversation/transcript log for a session."""
        from .models import MessageLog

        with Session(self.db_engine) as session:
            stmt = select(MessageLog).where(MessageLog.session_key == session_key).order_by(col(MessageLog.timestamp).asc())
            if role_filter:
                stmt = stmt.where(MessageLog.role == role_filter)
            rows = session.exec(stmt).all()

        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "tool_name": r.tool_name,
                "tool_args": r.tool_args,
                "tool_id": r.tool_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None
            }
            for r in rows
        ]

    def record_message(self, session_key: str, role: str, content: str = None, 
                       tool_name: str = None, tool_args: str = None, tool_id: str = None,
                       account_id: str = None):
        """Persist a message to the session log."""
        from .models import MessageLog
        entry = MessageLog(
            session_key=session_key,
            role=role,
            content=content,
            account_id=account_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_id=tool_id
        )
        with Session(self.db_engine) as session:
            session.add(entry)
            session.commit()

    # ── CSV Export ─────────────────────────────────────────────────────────

    def export_sessions_csv(self, start: Optional[date] = None, end: Optional[date] = None) -> str:
        """CSV export of session aggregates. Sovereign Spec Section 4.7"""
        data = self.get_sessions(start, end)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "session_key", "total_input", "total_output", "total_cost",
            "turn_count", "models", "first_turn", "last_turn",
        ])
        writer.writeheader()
        for s in data["sessions"]:
            s["models"] = ";".join(s["models"]) if isinstance(s["models"], list) else s["models"]
            writer.writerow(s)
        return output.getvalue()

    def export_daily_csv(self, start: Optional[date] = None, end: Optional[date] = None) -> str:
        """CSV export of daily rollup. Sovereign Spec Section 4.7"""
        data = self.get_daily(start, end)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["date", "input_tokens", "output_tokens", "cost", "turns"])
        writer.writeheader()
        for d in data:
            writer.writerow(d)
        return output.getvalue()
