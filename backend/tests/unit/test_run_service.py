"""生成任务服务单元测试 — 状态流转与后台执行。"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.generation_run import GenerationRun
from app.schemas.run import RunCreate
from app.schemas.requirement import AnalysisPayload, RequirementNode
from app.schemas.project import ProjectCreate, ProjectType
from app.services.run_service import RunService
from app.services.project_service import ProjectService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def project(db_session):
    svc = ProjectService(db_session)
    return svc.create(ProjectCreate(
        project_type=ProjectType.NEW,
        target_price_wan="30",
        quote_company="测试公司",
        quote_date=date(2026, 7, 17),
    ))


def test_create_run_with_pending_status(db_session, project):
    svc = RunService(db_session)
    run = svc.create_run(
        project_id=project.id,
        task_type="analysis",
    )
    assert run.status == "pending"
    assert run.task_type == "analysis"
    assert run.project_id == project.id


def test_run_status_transitions(db_session, project):
    svc = RunService(db_session)
    run = svc.create_run(project_id=project.id, task_type="analysis")

    svc.start_run(run.id)
    assert run.status == "running"

    payload = AnalysisPayload(
        overview="测试项目",
        requirements=[
            RequirementNode(
                id="r1",
                module="客户管理",
                feature="登录",
                description="用户登录",
                source_refs=["brief.docx"],
                complexity_weight=2,
            )
        ],
    )
    svc.complete_run(run.id, analysis_payload=payload)
    assert run.status == "succeeded"
    assert run.analysis_payload is not None


def test_run_failure_saves_error(db_session, project):
    svc = RunService(db_session)
    run = svc.create_run(project_id=project.id, task_type="analysis")

    svc.fail_run(run.id, error="Agent 调用超时")
    assert run.status == "failed"
    assert "超时" in run.error_message
