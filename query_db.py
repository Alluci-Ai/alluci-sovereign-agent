from sqlmodel import Session, select
from backend.database import engine as db_engine
from backend.models import AgentChannelSubscription

with Session(db_engine) as session:
    subs = session.exec(select(AgentChannelSubscription)).all()
    print(f"Total subscriptions: {len(subs)}")
    for sub in subs:
        print(sub)
