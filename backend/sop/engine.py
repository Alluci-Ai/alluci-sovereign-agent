
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select
from ..database import engine as db_engine
from ..models import SOPRecord

logger = logging.getLogger("SOPEngine")

class SOPEngine:
    """
    Sovereign SOP (Standard Operating Procedure) Engine.
    Executes predefined sequences with database persistence.
    """
    def __init__(self, engine=None):
        self.engine = engine or db_engine

    async def register_sop(self, name: str, description: str, steps: List[Dict[str, Any]]):
        with Session(self.engine) as session:
            sop = SOPRecord(
                name=name,
                description=description,
                steps={"steps": steps}
            )
            session.add(sop)
            session.commit()
            session.refresh(sop)
            return sop.id

    def get_sop(self, sop_id: int) -> Optional[SOPRecord]:
        with Session(self.engine) as session:
            return session.get(SOPRecord, sop_id)

    def list_sops(self) -> List[SOPRecord]:
        with Session(self.engine) as session:
            stmt = select(SOPRecord).where(SOPRecord.is_active == True)
            return session.exec(stmt).all()

# Global Singleton
sop_engine = SOPEngine()
