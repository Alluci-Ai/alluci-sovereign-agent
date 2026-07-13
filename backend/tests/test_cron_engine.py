import pytest
pytestmark = pytest.mark.unit

import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlmodel import Session, create_engine, SQLModel
from backend.cron_engine import CronEngine, ScheduleType
from backend.models import CronJob, CronRun

@pytest.fixture
def temp_db():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine

class TestCronEngineMultiAgent:

    def test_cron_isolation_crud(self, temp_db):
        engine = CronEngine(db_engine=temp_db)
        
        # Create a job for agent1
        data1 = {
            "name": "job1",
            "agent_id": "agent1",
            "schedule_type": ScheduleType.INTERVAL,
            "schedule_value": "10",
        }
        engine.create_job(data1)
        
        # Create a job for executive (default)
        data2 = {
            "name": "job2",
            "agent_id": "executive",
            "schedule_type": ScheduleType.INTERVAL,
            "schedule_value": "5",
        }
        engine.create_job(data2)
        
        # List jobs isolates
        jobs1 = engine.list_jobs(agent_id="agent1")
        assert len(jobs1) == 1
        assert jobs1[0]["name"] == "job1"
        
        jobs2 = engine.list_jobs(agent_id="executive")
        assert len(jobs2) == 1
        assert jobs2[0]["name"] == "job2"
        
        # Get job isolates
        assert engine.get_job(jobs1[0]["id"], agent_id="executive") is None
        assert engine.get_job(jobs1[0]["id"], agent_id="agent1") is not None
        
        # Update isolates
        res = engine.update_job(jobs1[0]["id"], {"name": "updated"}, agent_id="executive")
        assert res is None
        
        # Delete isolates
        res = engine.delete_job(jobs1[0]["id"], agent_id="executive")  # type: ignore
        assert res is False
        
        # Proper deletion
        res = engine.delete_job(jobs1[0]["id"], agent_id="agent1")
        assert res is True
        
        assert len(engine.list_jobs(agent_id="agent1")) == 0

    @pytest.mark.asyncio
    async def test_cron_execution_passes_agent_id(self, temp_db):
        mock_task_mgr = AsyncMock()
        engine = CronEngine(db_engine=temp_db, task_manager=mock_task_mgr)
        
        with Session(temp_db) as session:
            job = CronJob(
                name="exec_job",
                agent_id="sub_agent_99",
                schedule_type=ScheduleType.INTERVAL,
                schedule_value="10",
                payload="Do something"
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            
        await engine._execute_job(job, datetime.datetime.now(datetime.timezone.utc))
        
        mock_task_mgr.add_task.assert_called_once()
        # Assert agent_id="sub_agent_99" was passed as kwarg
        _, kwargs = mock_task_mgr.add_task.call_args
        assert kwargs.get("agent_id") == "sub_agent_99"

    @pytest.mark.asyncio
    async def test_cron_schedule_parsing(self, temp_db):
        """Validate that ScheduleType.CRON correctly utilizes the updated croniter."""
        engine = CronEngine(db_engine=temp_db)
        
        # Test CRON execution with an every-minute schedule
        now = datetime.datetime.now(datetime.timezone.utc)
        
        job = CronJob(
            name="cron_job",
            agent_id="test_agent",
            schedule_type=ScheduleType.CRON,
            schedule_value="* * * * *",
            last_run_at=now - datetime.timedelta(minutes=2)
        )
        
        # Since last_run_at is 2 mins ago and schedule is every minute, it should be due
        assert engine._is_due(job, now) is True
        
        # Test when last_run_at was 10 seconds ago (should not be due yet)
        job.last_run_at = now - datetime.timedelta(seconds=10)
        assert engine._is_due(job, now) is False
