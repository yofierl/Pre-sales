# Task 2 Backend: 材料分析和网页结构化草稿 (Steps 1-5)

## Context
This is built on top of Task 1 (Project CRUD with SQLite + integer money + JSON roles).
The current backend has: project model, project_service, projects api route.
You are adding: materials, generation_runs, file storage, material parsing, agent gateway, run service, and their APIs.

## Exact files to create/modify

### Create:
- `backend/app/models/material.py`
- `backend/app/models/generation_run.py`
- `backend/app/schemas/material.py`
- `backend/app/schemas/requirement.py`
- `backend/app/schemas/run.py`
- `backend/app/services/file_storage.py`
- `backend/app/services/material_parser.py`
- `backend/app/services/agent_gateway.py`
- `backend/app/services/run_service.py`
- `backend/app/api/routes/materials.py`
- `backend/app/api/routes/runs.py`
- `backend/alembic/versions/0002_create_materials_and_runs.py`
- `backend/tests/unit/test_material_parser.py`
- `backend/tests/unit/test_run_service.py`
- `backend/tests/integration/test_analysis_flow.py`

### Modify:
- `backend/app/models/__init__.py` - add Material, GenerationRun imports
- `backend/app/api/router.py` - add materials and runs routers

## Step 1: Write failing tests first (TDD)

### `backend/tests/unit/test_material_parser.py`

```python
"""单元测试：材料解析器。"""

import pytest
from pathlib import Path
from app.services.material_parser import merge_source_blocks, parse_material, SourceBlock


class TestMergeBlocks:
    def test_merge_blocks_uses_declared_precedence(self):
        blocks = [
            SourceBlock(source="image.png", priority=4, text="旧名称"),
            SourceBlock(source="brief.docx", priority=3, text="门户名称"),
            SourceBlock(source="user_input", priority=1, text="名称改为客户中心"),
        ]
        result = merge_source_blocks(blocks)
        assert result.blocks[0].source == "user_input"
        assert result.conflicts

    def test_broken_file_becomes_visible_failure(self, tmp_path):
        path = tmp_path / "broken.pdf"
        path.write_bytes(b"not a pdf")
        result = parse_material(path, "application/pdf")
        assert result.status == "failed"
        assert "broken.pdf" in result.error
```

### `backend/tests/unit/test_run_service.py`

```python
"""单元测试：RunService。"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.models.project import Project
from app.models.generation_run import GenerationRun
from app.services.run_service import RunService
from app.schemas.requirement import AnalysisPayload, RequirementNode


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def project(db_session):
    p = Project(
        name="测试项目",
        project_type="new",
        target_gross_cents=30_000_000,
        quote_company="测试公司",
        quote_date=date(2026, 7, 17),
        roles_json=[
            {"name": "产品", "unit_price_cents": 80_000, "is_required": True},
            {"name": "前端", "unit_price_cents": 85_000, "is_required": False},
        ],
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


class TestRunService:
    def test_start_analysis_creates_pending_run_and_returns_run_id(self, db_session, project):
        service = RunService(db_session)
        run = service.start_analysis(project.id, supplement="补充说明")
        assert run.id is not None
        assert run.status == "pending"
        assert run.project_id == project.id

    def test_fail_analysis_creates_record_with_no_project(self, db_session):
        service = RunService(db_session)
        with pytest.raises(ValueError, match="项目不存在"):
            service.start_analysis("nonexistent")
```

### `backend/tests/integration/test_analysis_flow.py`

```python
"""集成测试：分析流程。"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.project import Project


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


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
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


@pytest.fixture
def project_id(db_session):
    p = Project(
        name="测试项目",
        project_type="new",
        target_gross_cents=30_000_000,
        quote_company="测试公司",
        quote_date=date(2026, 7, 17),
        roles_json=[{"name": "产品", "unit_price_cents": 80_000, "is_required": True}],
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p.id


@pytest.fixture
def fake_agent():
    """Override the agent_gateway dependency with a fake that returns a predictable AnalysisPayload."""
    from app.schemas.requirement import AnalysisPayload, RequirementNode
    from app.services.agent_gateway import AgentGateway

    class FakeAgent:
        def analyze(self, blocks, supplement=None):
            return AnalysisPayload(
                overview="测试项目概述",
                requirements=[
                    RequirementNode(
                        id="r1",
                        module="门户",
                        feature="用户登录",
                        description="用户可以通过手机号登录系统",
                        source_refs=["test"],
                        complexity_weight=3,
                    )
                ],
            )

    return FakeAgent()


class TestAnalysisFlow:
    def test_analysis_run_returns_structured_draft(self, client, fake_agent, project_id):
        # Use dependency override for fake agent
        from app.services.agent_gateway import AgentGateway
        app.dependency_overrides[AgentGateway] = lambda: fake_agent
        try:
            response = client.post(
                f"/api/v1/projects/{project_id}/analysis-runs",
                json={"supplement": "需要客户门户"},
            )
            assert response.status_code == 202
            run_id = response.json()["run_id"]
            run = client.get(f"/api/v1/runs/{run_id}").json()
            assert run["status"] == "succeeded"
        finally:
            app.dependency_overrides.clear()
```

## Step 3: Schemas

### `backend/app/schemas/requirement.py`

```python
"""
结构化需求 Schema。

所有 Agent 输出必须经过此模型校验，确保字段完整、类型正确。
"""
from pydantic import BaseModel, Field, model_validator


class SourceBlock(BaseModel):
    """来源块，表示一个从材料中提取的信息片段。"""
    source: str
    priority: int = Field(ge=1, le=4)
    text: str | None = None
    image_path: str | None = None

    @model_validator(mode="after")
    def require_content(self) -> "SourceBlock":
        if not self.text and not self.image_path:
            raise ValueError("来源块必须包含文本或图片路径")
        return self


class RequirementNode(BaseModel):
    """结构化需求节点。"""
    id: str
    module: str
    submodule: str | None = None
    feature: str
    subfeature: str | None = None
    description: str
    source_refs: list[str] = Field(min_length=1)
    pending_confirmation: bool = False
    system_added: bool = False
    suggested_roles: list[str] = Field(default_factory=list)
    complexity_weight: int = Field(ge=1, le=5)


class AnalysisPayload(BaseModel):
    """分析结果载荷。"""
    suggested_project_name: str | None = None
    overview: str
    requirements: list[RequirementNode] = Field(min_length=1)
    conflicts: list[str] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)


class MergeResult(BaseModel):
    """合并结果。"""
    blocks: list[SourceBlock]
    conflicts: list[str] = Field(default_factory=list)


class ParseResult(BaseModel):
    """解析结果。"""
    status: str  # "succeeded" | "failed"
    blocks: list[SourceBlock] = Field(default_factory=list)
    error: str | None = None
```

### `backend/app/schemas/material.py`

```python
"""材料 Schema。"""
from datetime import datetime
from pydantic import BaseModel


class MaterialResponse(BaseModel):
    id: str
    project_id: str
    original_name: str
    file_type: str
    file_size: int
    storage_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialListResponse(BaseModel):
    items: list[MaterialResponse]
```

### `backend/app/schemas/run.py`

```python
"""生成记录 Schema。"""
from datetime import datetime
from pydantic import BaseModel
from app.schemas.requirement import AnalysisPayload


class RunResponse(BaseModel):
    id: str
    project_id: str
    task_type: str
    status: str
    error_message: str | None = None
    analysis_payload: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalysisRunRequest(BaseModel):
    supplement: str | None = None


class AnalysisRunResponse(BaseModel):
    run_id: str
    status: str


class ConfirmedRequirementsUpdate(BaseModel):
    requirements: list[dict]
    overview: str | None = None


class RetryResponse(BaseModel):
    run_id: str
    status: str
```

## Step 3: Models

### `backend/app/models/material.py`

```python
"""材料模型。"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Material(Base):
    __tablename__ = "material"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
```

### `backend/app/models/generation_run.py`

```python
"""生成记录模型。"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class GenerationRun(Base):
    __tablename__ = "generation_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "analysis" | "pricing"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # pending -> running -> succeeded | failed
    supplement: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmed_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pricing_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
```

### `backend/app/models/__init__.py` (modify)
```python
from app.models.project import Project, ProjectStage
from app.models.material import Material
from app.models.generation_run import GenerationRun
```

## Step 4: Services

### `backend/app/services/file_storage.py`

```python
"""文件存储服务。"""
import uuid
from pathlib import Path


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}


class FileStorage:
    def __init__(self, root: str | Path = "storage") -> None:
        self.root = Path(root)

    def save(self, project_id: str, original_name: str, content: bytes) -> Path:
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}")
        project_dir = self.root / project_id / "materials"
        project_dir.mkdir(parents=True, exist_ok=True)
        target = project_dir / f"{uuid.uuid4()}{suffix}"
        target.write_bytes(content)
        return target

    def delete(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()

    def delete_project_dir(self, project_id: str) -> None:
        project_dir = self.root / project_id
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
```

### `backend/app/services/material_parser.py`

```python
"""材料解析器。"""
import io
from pathlib import Path
from typing import IO
from app.schemas.requirement import SourceBlock, MergeResult, ParseResult


def parse_material(path: str | Path, mime_type: str) -> ParseResult:
    """解析单个材料文件，提取文本块。"""
    path = Path(path)
    try:
        content = path.read_bytes()
        if mime_type == "application/pdf":
            return _parse_pdf(content, path.name)
        elif mime_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
            return _parse_docx(content, path.name)
        elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return _parse_xlsx(content, path.name)
        elif mime_type.startswith("image/"):
            return _parse_image(path, path.name)
        else:
            return ParseResult(status="failed", error=f"不支持的 MIME 类型: {mime_type}")
    except Exception as e:
        return ParseResult(status="failed", error=f"解析 {path.name} 失败: {e!s}")


def _parse_pdf(content: bytes, filename: str) -> ParseResult:
    """解析 PDF 文件。"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            return ParseResult(status="failed", error=f"{filename} 未能提取到文本内容")
        return ParseResult(
            status="succeeded",
            blocks=[SourceBlock(source=filename, priority=4, text=text.strip())],
        )
    except Exception as e:
        return ParseResult(status="failed", error=f"{filename} 解析失败: {e!s}")


def _parse_docx(content: bytes, filename: str) -> ParseResult:
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        if not text.strip():
            return ParseResult(status="failed", error=f"{filename} 未能提取到文本内容")
        return ParseResult(
            status="succeeded",
            blocks=[SourceBlock(source=filename, priority=3, text=text.strip())],
        )
    except Exception as e:
        return ParseResult(status="failed", error=f"{filename} 解析失败: {e!s}")


def _parse_xlsx(content: bytes, filename: str) -> ParseResult:
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(content), read_only=True)
        lines = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    lines.append(" | ".join(cells))
        text = "\n".join(lines)
        if not text.strip():
            return ParseResult(status="failed", error=f"{filename} 未能提取到表格内容")
        return ParseResult(
            status="succeeded",
            blocks=[SourceBlock(source=filename, priority=3, text=text.strip())],
        )
    except Exception as e:
        return ParseResult(status="failed", error=f"{filename} 解析失败: {e!s}")


def _parse_image(path: Path, filename: str) -> ParseResult:
    return ParseResult(
        status="succeeded",
        blocks=[SourceBlock(source=filename, priority=4, image_path=str(path.resolve()))],
    )


def merge_source_blocks(blocks: list[SourceBlock]) -> MergeResult:
    """按优先级合并来源块。优先级数字越小优先级越高（1=用户输入最高）。"""
    if not blocks:
        return MergeResult(blocks=[], conflicts=[])
    conflicts = []
    seen_sources = set()
    deduped = []
    for block in sorted(blocks, key=lambda b: (b.priority, b.source)):
        key = (block.source, block.text, block.image_path)
        if key not in seen_sources:
            seen_sources.add(key)
            deduped.append(block)
        else:
            conflicts.append(f"重复来源块: {block.source}")
    deduped.sort(key=lambda b: b.priority)
    return MergeResult(blocks=deduped, conflicts=conflicts)
```

### `backend/app/services/agent_gateway.py`

```python
"""Agent 网关 - 定义 Agent 调用边界。"""
from typing import Protocol
from app.schemas.requirement import SourceBlock, AnalysisPayload


class AgentGateway(Protocol):
    """Agent 网关协议。实现类必须提供 analyze 方法。"""

    def analyze(self, blocks: list[SourceBlock], supplement: str | None = None) -> AnalysisPayload:
        """分析材料并返回结构化需求。"""
        raise NotImplementedError


class OpenAIAgentGateway:
    """基于 OpenAI 的 Agent 实现。"""

    def __init__(self, model: str = "gpt-4o") -> None:
        self.model = model

    def analyze(self, blocks: list[SourceBlock], supplement: str | None = None) -> AnalysisPayload:
        """调用 OpenAI 分析材料。实现时完成。"""
        raise NotImplementedError("OpenAI Agent 尚未实现")


class FakeAgentGateway:
    """测试用假 Agent。"""

    def analyze(self, blocks: list[SourceBlock], supplement: str | None = None) -> AnalysisPayload:
        from app.schemas.requirement import AnalysisPayload, RequirementNode

        return AnalysisPayload(
            overview="基于材料分析的项目概述",
            requirements=[
                RequirementNode(
                    id="r1",
                    module="门户",
                    feature="用户登录",
                    description="用户可以通过手机号登录系统",
                    source_refs=[b.source for b in blocks] if blocks else ["默认来源"],
                    complexity_weight=3,
                )
            ],
            unanswered_questions=[],
        )
```

### `backend/app/services/run_service.py`

```python
"""生成记录服务。"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.generation_run import GenerationRun
from app.schemas.requirement import AnalysisPayload, RequirementNode
from app.services.material_parser import parse_material, merge_source_blocks, SourceBlock


class RunService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def start_analysis(self, project_id: str, supplement: str | None = None) -> GenerationRun:
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("项目不存在")
        run = GenerationRun(
            project_id=project_id,
            task_type="analysis",
            status="pending",
            supplement=supplement,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def run_analysis_in_background(self, run_id: str) -> None:
        """执行分析任务（由 BackgroundTasks 调用）。"""
        run = self.db.query(GenerationRun).filter(GenerationRun.id == run_id).first()
        if not run:
            return
        try:
            run.status = "running"
            self.db.commit()
            # Use FakeAgentGateway for now
            from app.services.agent_gateway import FakeAgentGateway
            agent = FakeAgentGateway()
            blocks: list[SourceBlock] = []
            # In real flow, parse materials here
            payload = agent.analyze(blocks, supplement=run.supplement)
            run.analysis_payload = payload.model_dump()
            run.status = "succeeded"
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
        finally:
            run.updated_at = datetime.now()
            self.db.commit()

    def get_run(self, run_id: str) -> GenerationRun | None:
        return self.db.query(GenerationRun).filter(GenerationRun.id == run_id).first()

    def retry_run(self, run_id: str) -> GenerationRun:
        existing = self.get_run(run_id)
        if not existing:
            raise ValueError("生成记录不存在")
        new_run = GenerationRun(
            project_id=existing.project_id,
            task_type=existing.task_type,
            status="pending",
            supplement=existing.supplement,
        )
        self.db.add(new_run)
        self.db.commit()
        self.db.refresh(new_run)
        return new_run

    def save_confirmed_requirements(self, project_id: str, requirements: list[dict], overview: str | None = None) -> None:
        """将确认后的需求保存到最新一条 analysis 类型的生成记录。"""
        latest = (
            self.db.query(GenerationRun)
            .filter(
                GenerationRun.project_id == project_id,
                GenerationRun.task_type == "analysis",
                GenerationRun.status == "succeeded",
            )
            .order_by(GenerationRun.created_at.desc())
            .first()
        )
        if not latest:
            raise ValueError("没有已完成的分析记录")
        latest.confirmed_requirements = {"overview": overview or "", "requirements": requirements}
        if overview:
            if latest.analysis_payload:
                latest.analysis_payload["overview"] = overview
        # Update project stage
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.stage = "draft_ready"
        self.db.commit()
```

## Step 5: Routes

### `backend/app/api/routes/materials.py`

```python
"""材料上传与删除。"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.material import Material
from app.schemas.material import MaterialResponse, MaterialListResponse
from app.services.file_storage import FileStorage

router = APIRouter()
storage = FileStorage()


@router.post("/{project_id}/materials", response_model=MaterialResponse, status_code=201)
def upload_material(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")
    content = file.file.read()
    try:
        saved_path = storage.save(project_id, file.filename, content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    material = Material(
        project_id=project_id,
        original_name=file.filename,
        file_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        storage_path=str(saved_path),
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.get("/{project_id}/materials", response_model=MaterialListResponse)
def list_materials(project_id: str, db: Session = Depends(get_db)):
    items = db.query(Material).filter(Material.project_id == project_id).order_by(Material.created_at.desc()).all()
    return MaterialListResponse(items=items)


@router.delete("/{project_id}/materials/{material_id}", status_code=204)
def delete_material(project_id: str, material_id: str, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id, Material.project_id == project_id).first()
    if not material:
        raise HTTPException(404, "材料不存在")
    storage.delete(material.storage_path)
    db.delete(material)
    db.commit()
```

### `backend/app/api/routes/runs.py`

```python
"""分析报价任务管理。"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.generation_run import GenerationRun
from app.models.project import Project
from app.schemas.run import (
    RunResponse,
    AnalysisRunRequest,
    AnalysisRunResponse,
    ConfirmedRequirementsUpdate,
    RetryResponse,
)
from app.services.run_service import RunService

router = APIRouter()


@router.post("/{project_id}/analysis-runs", response_model=AnalysisRunResponse, status_code=202)
def start_analysis_run(
    project_id: str,
    body: AnalysisRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    service = RunService(db)
    try:
        run = service.start_analysis(project_id, supplement=body.supplement)
    except ValueError as e:
        raise HTTPException(400, str(e))
    background_tasks.add_task(service.run_analysis_in_background, run.id)
    return AnalysisRunResponse(run_id=run.id, status=run.status)


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    service = RunService(db)
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(404, "生成记录不存在")
    return run


@router.post("/runs/{run_id}/retry", response_model=RetryResponse)
def retry_run(run_id: str, db: Session = Depends(get_db)):
    service = RunService(db)
    try:
        new_run = service.retry_run(run_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RetryResponse(run_id=new_run.id, status=new_run.status)


@router.put("/{project_id}/confirmed-requirements", status_code=200)
def save_confirmed_requirements(
    project_id: str,
    body: ConfirmedRequirementsUpdate,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")
    service = RunService(db)
    try:
        service.save_confirmed_requirements(project_id, body.requirements, overview=body.overview)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}
```

### `backend/app/api/router.py` (modify)
```python
"""API 路由。"""
from fastapi import APIRouter
from app.api.routes import projects, materials, runs

router = APIRouter(prefix="/api/v1")

router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(materials.router, prefix="/projects", tags=["materials"])
router.include_router(runs.router, prefix="/projects", tags=["runs"])
```

### Migration

`backend/alembic/versions/0002_create_materials_and_runs.py`:

```python
"""创建 material 和 generation_run 表。"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "generation_run",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("task_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("supplement", sa.Text(), nullable=True),
        sa.Column("analysis_payload", sa.JSON(), nullable=True),
        sa.Column("confirmed_requirements", sa.JSON(), nullable=True),
        sa.Column("pricing_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("generation_run")
    op.drop_table("material")
```

## Report

After implementation, write report to `.superpowers/sdd/task2-backend-report.md` with:
1. List of files created/modified
2. Test results summary
3. Any concerns
