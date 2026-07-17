"""项目 API 集成测试（SQLite + 整数金额 + JSON 角色契约）。"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.project import Project  # noqa: F401


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


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


SAMPLE_PAYLOAD = {
    "name": "客户门户",
    "project_type": "new",
    "target_price_wan": "30",
    "quote_company": "重庆酷小贝软件开发有限公司",
    "quote_date": "2026-07-17",
    "customer_name": "示例客户",
    "roles": [],
}


class TestNewContract:
    """验证新数据形态：整数金额、JSON 角色、四阶段、stage 不可写。"""

    def test_create_project_stores_integer_money_and_role_json(self, client: TestClient) -> None:
        response = client.post("/api/v1/projects", json=SAMPLE_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert body["target_gross_cents"] == 30_000_000
        role_names = [r["name"] for r in body["roles"]]
        assert role_names == ["产品", "前端", "后端", "测试"]
        assert body["roles"][0]["unit_price_cents"] == 80_000
        assert body["stage"] == "input"

    def test_project_stage_is_not_writable_by_client(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/projects", json=SAMPLE_PAYLOAD)
        project_id = create_resp.json()["id"]
        response = client.patch(
            f"/api/v1/projects/{project_id}", json={"stage": "completed"},
        )
        assert response.status_code == 422

    def test_project_required_roles_are_present(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json=SAMPLE_PAYLOAD)
        roles = resp.json()["roles"]
        required = [r for r in roles if r["is_required"]]
        required_names = {r["name"] for r in required}
        assert "产品" in required_names
        assert "测试" in required_names

    def test_project_roles_reject_missing_required(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json={
            **SAMPLE_PAYLOAD,
            "roles": [{"name": "前端", "unit_price_cents": 85_000}],
        })
        assert resp.status_code == 400

    def test_create_project_without_name(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json={**SAMPLE_PAYLOAD, "name": None})
        assert resp.status_code == 201
        assert resp.json()["name"] is None

    def test_target_price_must_be_positive(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json={**SAMPLE_PAYLOAD, "target_price_wan": "0"})
        assert resp.status_code == 422


class TestCrud:
    def test_get_project(self, client: TestClient) -> None:
        create = client.post("/api/v1/projects", json=SAMPLE_PAYLOAD)
        pid = create.json()["id"]
        resp = client.get(f"/api/v1/projects/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_get_project_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/projects/nonexistent")
        assert resp.status_code == 404

    def test_list_projects(self, client: TestClient) -> None:
        client.post("/api/v1/projects", json=SAMPLE_PAYLOAD)
        client.post("/api/v1/projects", json={**SAMPLE_PAYLOAD, "name": "项目二"})
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_update_project(self, client: TestClient) -> None:
        create = client.post("/api/v1/projects", json=SAMPLE_PAYLOAD)
        pid = create.json()["id"]
        resp = client.patch(f"/api/v1/projects/{pid}", json={"name": "已改名"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "已改名"

    def test_delete_project(self, client: TestClient) -> None:
        create = client.post("/api/v1/projects", json=SAMPLE_PAYLOAD)
        pid = create.json()["id"]
        resp = client.delete(f"/api/v1/projects/{pid}")
        assert resp.status_code == 204
        get_resp = client.get(f"/api/v1/projects/{pid}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient) -> None:
        resp = client.delete("/api/v1/projects/nonexistent")
        assert resp.status_code == 404
