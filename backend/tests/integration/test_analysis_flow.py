"""分析流程集成测试 — 使用假 Agent 验证完整链路。"""

from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.project import Project  # noqa: F401
from app.models.generation_run import GenerationRun  # noqa: F401
from app.models.material import Material  # noqa: F401
from app.schemas.requirement import AnalysisPayload, RequirementNode
from app.services.run_service import RunService
from app.services.agent_gateway import AgentGateway
from app.dependencies import get_agent_gateway


SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class FakeAgent:
    def analyze(self, blocks, supplement=None):
        return AnalysisPayload(
            suggested_project_name="客户门户",
            overview="客户管理门户开发项目",
            requirements=[
                RequirementNode(
                    id="r1",
                    module="客户管理",
                    submodule=None,
                    feature="用户登录",
                    subfeature=None,
                    description="支持手机号和邮箱登录",
                    source_refs=["brief.docx"],
                    pending_confirmation=False,
                    system_added=False,
                    suggested_roles=["后端"],
                    complexity_weight=2,
                ),
                RequirementNode(
                    id="r2",
                    module="客户管理",
                    submodule=None,
                    feature="权限管理",
                    subfeature=None,
                    description="支持角色管理和权限分配",
                    source_refs=["brief.docx"],
                    pending_confirmation=False,
                    system_added=True,
                    suggested_roles=["后端", "前端"],
                    complexity_weight=3,
                ),
            ],
            conflicts=["brief.docx 和 user_input 对项目名称描述不一致"],
            unanswered_questions=["是否需要对接现有 SSO？"],
        )


@pytest.fixture()
def client(db_session, fake_agent):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_agent():
        return fake_agent

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_agent_gateway] = override_agent
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def fake_agent():
    return FakeAgent()


@pytest.fixture()
def project_id(client):
    resp = client.post(
        "/api/v1/projects",
        json={
            "project_type": "new",
            "target_price_wan": "30",
            "quote_company": "测试公司",
            "quote_date": "2026-07-17",
        },
    )
    return resp.json()["id"]


def test_analysis_run_returns_structured_draft(client, fake_agent, project_id):
    response = client.post(
        f"/api/v1/projects/{project_id}/analysis-runs",
        json={"supplement": "需要客户门户"},
    )
    assert response.status_code == 202
    run_id = response.json()["run_id"]

    run = client.get(f"/api/v1/runs/{run_id}").json()
    assert run["status"] == "succeeded"
    assert run["analysis_payload"]["requirements"][0]["source_refs"]


def test_confirm_requirements_updates_project_stage(client, fake_agent, project_id):
    resp = client.put(
        f"/api/v1/projects/{project_id}/confirmed-requirements",
        json={
            "requirements": [
                {
                    "id": "r1",
                    "module": "客户管理",
                    "feature": "用户登录",
                    "description": "手机号邮箱登录",
                    "source_refs": ["brief.docx"],
                    "complexity_weight": 2,
                    "pending_confirmation": False,
                    "system_added": False,
                    "suggested_roles": ["后端"],
                }
            ]
        },
    )
    assert resp.status_code == 200
    project = client.get(f"/api/v1/projects/{project_id}").json()
    assert project["stage"] == "draft_ready"


def test_material_upload_requires_existing_project(client, fake_agent, project_id):
    response = client.post(
        "/api/v1/projects/non-existent-id/materials",
        files={"file": ("test.pdf", b"dummy content", "application/pdf")},
    )
    assert response.status_code == 404


def test_list_materials_empty_for_new_project(client, fake_agent, project_id):
    response = client.get(f"/api/v1/projects/{project_id}/materials")
    assert response.status_code == 200
    assert response.json()["items"] == []
