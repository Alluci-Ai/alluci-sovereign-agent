"""Add skills_manifest to AgentRecord and migrate data

Revision ID: d7915fbb5795
Revises: d7915fbb5794
Create Date: 2026-07-02 11:00:00.000000

"""
from typing import Sequence, Union
import json
import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision: str = 'd7915fbb5795'
down_revision: Union[str, None] = 'd7915fbb5794'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

Base = declarative_base()

class AgentRecord(Base):
    __tablename__ = 'agent_record'
    id = sa.Column(sa.String, primary_key=True)
    tools_manifest = sa.Column(sa.JSON)
    skills_manifest = sa.Column(sa.JSON)

def get_skill_categories():
    categories = {}
    dirs_to_scan = [
        os.path.expanduser("~/.polytope/skills"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../alluci_vault/skills"))
    ]
    for d in dirs_to_scan:
        if not os.path.exists(d):
            continue
        try:
            for filename in os.listdir(d):
                if filename.endswith(".json"):
                    file_path = os.path.join(d, filename)
                    try:
                        with open(file_path, "r") as f:
                            data = json.load(f)
                            if "id" in data and "category" in data:
                                categories[data["id"]] = data["category"].upper()
                    except Exception:
                        pass
        except Exception:
            pass
    return categories

def upgrade() -> None:
    # 1. Add the column
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('skills_manifest', sa.JSON(), server_default='{}', nullable=True))
        
    # 2. Migrate Data
    bind = op.get_bind()
    session = Session(bind=bind)
    
    categories = get_skill_categories()
    
    for agent in session.query(AgentRecord).all():
        if agent.tools_manifest:
            try:
                # Handle both stringified JSON and dicts (depending on SQLite JSON vs String type)
                if isinstance(agent.tools_manifest, str):
                    tools_data = json.loads(agent.tools_manifest)
                else:
                    tools_data = agent.tools_manifest
                
                if isinstance(tools_data, dict):
                    new_tools = {}
                    new_skills = {}
                    for item_id, item_val in tools_data.items():
                        cat = categories.get(item_id, "TOOL")
                        if cat in ["FRAMEWORK", "MINDSET", "KNOWLEDGE"]:
                            new_skills[item_id] = item_val
                        else:
                            new_tools[item_id] = item_val
                            
                    agent.tools_manifest = new_tools  # type: ignore[assignment]
                    agent.skills_manifest = new_skills  # type: ignore[assignment]
            except Exception as e:
                print(f"Failed to migrate agent {agent.id}: {e}")
                
    session.commit()


def downgrade() -> None:
    # 1. Reverse Data Migration (Merge skills_manifest back into tools_manifest)
    bind = op.get_bind()
    session = Session(bind=bind)
    
    for agent in session.query(AgentRecord).all():
        if agent.skills_manifest:
            try:
                if isinstance(agent.skills_manifest, str):
                    skills_data = json.loads(agent.skills_manifest)
                else:
                    skills_data = agent.skills_manifest
                    
                if isinstance(agent.tools_manifest, str):
                    tools_data = json.loads(agent.tools_manifest) if agent.tools_manifest else {}
                else:
                    tools_data = agent.tools_manifest or {}
                    
                if isinstance(skills_data, dict) and isinstance(tools_data, dict):
                    merged_tools = {**tools_data, **skills_data}
                    agent.tools_manifest = merged_tools  # type: ignore[assignment]
            except Exception as e:
                print(f"Failed to downgrade agent {agent.id}: {e}")
                
    session.commit()

    # 2. Drop the column
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.drop_column('skills_manifest')
