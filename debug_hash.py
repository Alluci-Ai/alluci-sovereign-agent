import asyncio
import json
import hashlib
from backend.models import AuditLog
from backend.database import engine as db_engine
from sqlmodel import Session, select, SQLModel

SQLModel.metadata.create_all(db_engine)

with Session(db_engine) as session:
    log = AuditLog(event_id="test", event="test", details="test")
    session.add(log)
    session.commit()
    session.refresh(log)
    data = json.dumps([log.model_dump(exclude={"verus_txid", "vdxf_key", "anchored_timestamp"})], default=str)
    print(data)

    log.verus_txid = "test_tx"
    session.add(log)
    session.commit()
    session.refresh(log)

    data2 = json.dumps([log.model_dump(exclude={"verus_txid", "vdxf_key", "anchored_timestamp"})], default=str)
    print(data2)
    print(data == data2)
