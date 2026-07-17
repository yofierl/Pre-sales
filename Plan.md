# 售前知识工具精简版实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` (recommended) or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有项目骨架改造成一个单实例售前工具：用户上传材料、在网页确认结构化需求、按目标价格分配工时，并导出 Excel 报价单和 Word 产品文档。

**Architecture:** FastAPI 同时提供 API 和 Vue 静态页面，SQLite 保存四类核心数据，本地目录保存上传与导出文件。后台任务只处理材料分析和报价生成，业务代码使用接口层与服务层，不设置仓储层。

**Tech Stack:** Python 3.12+、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic、SQLite、OpenAI SDK、pypdf、python-docx、openpyxl、Vue 3、TypeScript、Vite、Element Plus、pytest、Vitest、Playwright。

## 全局约束

- 以 [Requirement Design.md](./Requirement%20Design.md) 和 [精简设计](./docs/superpowers/specs/2026-07-17-presales-agent-simplified-design.md) 为唯一需求依据。
- 根目录 `slice1.md`～`slice10.md` 已废弃，不再作为实施依据。
- 单实例、低并发，不实现登录、鉴权、权限、项目归属和安全审查。
- 数据库使用 SQLite；不使用 MySQL、PyMySQL 和 Docker Compose。
- 金额按“分”存储为整数；工时按“半天单位”存储为整数。
- 税率固定为 6%，合格报价区间为目标含税价的 97%～103%。
- 产品和测试角色必选，项目总工时分别不少于 0.5 人天。
- 单个角色、单个工作包为 0.5～3 人天。
- 不保存独立基准工时，不实现 Word 草稿重新上传。
- Agent 输出必须经过 Pydantic 模型校验，金额由后端确定性计算。
- 失败重试创建新的生成记录，不覆盖旧记录。
- 每个任务遵循测试先行、最小实现、完整验证和独立提交。
- 当前目录未检测到 Git 元数据；提交步骤应在正式 Git 工作区执行，若执行环境仍无 Git，则只完成对应验证并记录检查点。

## 目标文件结构

```text
backend/app/
├── api/routes/
│   ├── projects.py          # 项目创建、更新、删除
│   ├── materials.py         # 材料上传与删除
│   ├── runs.py              # 分析、报价、轮询和方案选择
│   └── artifacts.py         # 导出与下载
├── core/config.py
├── db/session.py
├── models/
│   ├── project.py
│   ├── material.py
│   ├── generation_run.py
│   └── artifact.py
├── schemas/
│   ├── project.py
│   ├── material.py
│   ├── requirement.py
│   ├── run.py
│   └── pricing.py
└── services/
    ├── project_service.py
    ├── file_storage.py
    ├── material_parser.py
    ├── agent_gateway.py
    ├── run_service.py
    ├── pricing_service.py
    ├── quotation_exporter.py
    └── product_doc_exporter.py

frontend/src/
├── api/
│   ├── projects.ts
│   ├── materials.ts
│   ├── runs.ts
│   └── artifacts.ts
├── views/
│   ├── ProjectListView.vue
│   └── ProjectWorkspaceView.vue
├── components/
│   ├── ProjectForm.vue
│   ├── ProjectSetupStep.vue
│   ├── RequirementDraftEditor.vue
│   ├── PricingStep.vue
│   ├── ExportStep.vue
│   └── HistoryDrawer.vue
└── types/
    ├── project.ts
    ├── requirement.ts
    ├── run.ts
    └── pricing.ts
```

---

### Task 1：切换 SQLite 并建立两页面项目骨架

**交付结果：** 用户可以在项目列表中新建项目并进入项目工作台；项目、角色和目标报价写入 SQLite。

**Files:**

- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/app/models/project.py`
- Delete: `backend/app/models/project_role.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/project.py`
- Create: `backend/app/services/project_service.py`
- Delete: `backend/app/repositories/project_repository.py`
- Modify: `backend/app/api/routes/projects.py`
- Replace: `backend/alembic/versions/0001_create_projects.py`
- Modify: `backend/tests/integration/test_projects_api.py`
- Delete: `compose.yaml`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/ProjectListView.vue`
- Create: `frontend/src/views/ProjectWorkspaceView.vue`
- Delete: `frontend/src/views/ProjectCreateView.vue`
- Modify: `frontend/src/components/ProjectForm.vue`
- Modify: `frontend/src/types/project.ts`
- Modify: `frontend/tests/unit/ProjectForm.spec.ts`

**Interfaces:**

- Produces: `ProjectService(db: Session)`，提供 `create`、`list`、`get`、`update`、`delete`。
- Produces: `Project.roles_json: list[RoleConfig]`，角色单价使用 `unit_price_cents: int`。
- Produces: `Project.target_gross_cents: int`，由万元输入转换得到。
- Produces: 前端只保留 `/projects` 和 `/projects/:id` 两个路由。

- [ ] **Step 1：先修改项目 API 测试，固定 SQLite 数据形态**

将 `backend/tests/integration/test_projects_api.py` 的核心断言改为：

```python
def test_create_project_stores_integer_money_and_role_json(client):
    response = client.post(
        "/api/v1/projects",
        json={
            "name": "客户门户",
            "project_type": "new",
            "target_price_wan": "30",
            "quote_company": "重庆酷小贝软件开发有限公司",
            "quote_date": "2026-07-17",
            "customer_name": "示例客户",
            "roles": [],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["target_gross_cents"] == 30_000_000
    assert [role["name"] for role in body["roles"]] == ["产品", "前端", "后端", "测试"]
    assert body["roles"][0]["unit_price_cents"] == 80_000
    assert body["stage"] == "input"


def test_project_status_is_not_writable_by_client(client, created_project):
    response = client.patch(
        f"/api/v1/projects/{created_project['id']}",
        json={"stage": "completed"},
    )
    assert response.status_code == 422
```

- [ ] **Step 2：运行测试，确认旧模型不满足新契约**

Run:

```powershell
Set-Location backend
python -m pytest tests/integration/test_projects_api.py -q
```

Expected: FAIL，响应仍使用字符串 `target_price`、独立 `project_role` 表和旧状态枚举。

- [ ] **Step 3：实现 SQLite 配置、项目模型和项目服务**

`backend/app/core/config.py` 的数据库默认值：

```python
database_url: str = "sqlite:///./data/shouqian.db"
```

`backend/app/db/session.py` 创建引擎时按数据库类型设置参数：

```python
from pathlib import Path


connect_args = {"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {}
if settings.database_url.startswith("sqlite:///./"):
    Path(settings.database_url.removeprefix("sqlite:///./")).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
```

`backend/app/models/project.py` 使用四阶段状态和 JSON 角色：

```python
class ProjectStage(str, Enum):
    INPUT = "input"
    DRAFT_READY = "draft_ready"
    QUOTE_READY = "quote_ready"
    COMPLETED = "completed"


class Project(Base):
    __tablename__ = "project"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = mapped_column(String(255), nullable=True)
    project_type = mapped_column(String(20), nullable=False)
    target_gross_cents = mapped_column(Integer, nullable=False)
    quote_company = mapped_column(String(255), nullable=False)
    quote_date = mapped_column(Date, nullable=False)
    customer_name = mapped_column(String(255), nullable=True)
    roles_json = mapped_column(JSON, nullable=False)
    stage = mapped_column(String(20), nullable=False, default=ProjectStage.INPUT.value)
    selected_run_id = mapped_column(String(36), nullable=True)
    selected_scenario_id = mapped_column(String(64), nullable=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
```

在 `backend/app/services/project_service.py` 中直接使用 SQLAlchemy：

```python
DEFAULT_ROLES = [
    {"name": "产品", "unit_price_cents": 80_000, "is_required": True},
    {"name": "前端", "unit_price_cents": 85_000, "is_required": False},
    {"name": "后端", "unit_price_cents": 85_000, "is_required": False},
    {"name": "测试", "unit_price_cents": 75_000, "is_required": True},
]


def wan_to_cents(value: Decimal) -> int:
    return int((value * Decimal("1000000")).quantize(Decimal("1")))


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: ProjectCreate) -> Project:
        roles = [role.model_dump() for role in data.roles] or DEFAULT_ROLES
        role_names = {role["name"] for role in roles}
        if not {"产品", "测试"}.issubset(role_names):
            raise ValueError("产品和测试角色不可删除")
        project = Project(
            name=data.name,
            project_type=data.project_type.value,
            target_gross_cents=wan_to_cents(data.target_price_wan),
            quote_company=data.quote_company,
            quote_date=data.quote_date,
            customer_name=data.customer_name,
            roles_json=roles,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project
```

路由只负责解析、调用服务和转换响应。删除 `ProjectRepository` 和 `ProjectRole`。

- [ ] **Step 4：更新迁移和依赖**

修改 `backend/pyproject.toml`，删除 `pymysql`。重写尚未发布的 `0001_create_projects.py`，只创建 `project` 表，并将 `roles_json` 定义为 JSON、金额定义为 Integer。

删除 `compose.yaml`。首次本地启动前创建 `backend/data/`，SQLite 文件由 Alembic 创建。

- [ ] **Step 5：运行后端测试，确认项目链路通过**

Run:

```powershell
Set-Location backend
python -m alembic upgrade head
python -m pytest tests/integration/test_projects_api.py -q
```

Expected: PASS；生成 `backend/data/shouqian.db`，不需要 MySQL 服务。

- [ ] **Step 6：合并前端页面并更新组件测试**

`frontend/src/router/index.ts` 只保留：

```typescript
const routes = [
  { path: '/', redirect: '/projects' },
  { path: '/projects', component: () => import('@/views/ProjectListView.vue') },
  { path: '/projects/:id', component: () => import('@/views/ProjectWorkspaceView.vue') },
]
```

项目列表中的“新建项目”打开 `ProjectForm` 对话框，创建成功后进入工作台。`ProjectWorkspaceView.vue` 先渲染四步步骤条和第一步项目参数区域：

```vue
<el-steps :active="activeStep" finish-status="success">
  <el-step title="参数与材料" />
  <el-step title="需求草稿" />
  <el-step title="工时与报价" />
  <el-step title="文件导出" />
</el-steps>
```

前端 `RoleConfig.unit_price_cents` 使用整数，表单展示时除以 100，提交时乘以 100。

- [ ] **Step 7：验证前端并提交**

Run:

```powershell
Set-Location frontend
npm run test -- ProjectForm.spec.ts
npm run build
```

Expected: Vitest PASS；Vite build PASS；项目只有两个可访问路由。

Commit:

```powershell
git add backend frontend "Requirement Design.md" Plan.md
git commit -m "refactor: simplify project foundation with sqlite"
```

---

### Task 2：材料分析和网页结构化草稿

**交付结果：** 用户可以上传组合材料，启动分析任务，在网页编辑结构化需求并确认快照。

**Files:**

- Create: `backend/app/models/material.py`
- Create: `backend/app/models/generation_run.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/material.py`
- Create: `backend/app/schemas/requirement.py`
- Create: `backend/app/schemas/run.py`
- Create: `backend/app/services/file_storage.py`
- Create: `backend/app/services/material_parser.py`
- Create: `backend/app/services/agent_gateway.py`
- Create: `backend/app/services/run_service.py`
- Create: `backend/app/api/routes/materials.py`
- Create: `backend/app/api/routes/runs.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/alembic/versions/0002_create_materials_and_runs.py`
- Create: `backend/tests/unit/test_material_parser.py`
- Create: `backend/tests/unit/test_run_service.py`
- Create: `backend/tests/integration/test_analysis_flow.py`
- Create: `frontend/src/api/materials.ts`
- Create: `frontend/src/api/runs.ts`
- Create: `frontend/src/types/requirement.ts`
- Create: `frontend/src/types/run.ts`
- Create: `frontend/src/components/ProjectSetupStep.vue`
- Create: `frontend/src/components/RequirementDraftEditor.vue`
- Modify: `frontend/src/views/ProjectWorkspaceView.vue`

**Interfaces:**

- Produces: `RequirementNode`，包含 `id`、层级字段、描述、来源、待确认标记、补充标记、角色建议和权重。
- Produces: `GenerationRun`，任务类型为 `analysis` 或 `pricing`，状态为 `pending/running/succeeded/failed`。
- Produces: `POST /api/v1/projects/{id}/analysis-runs` 和 `GET /api/v1/runs/{run_id}`。
- Produces: `PUT /api/v1/projects/{id}/confirmed-requirements`，保存确认后的不可变需求快照。

- [ ] **Step 1：编写材料解析和分析流程失败测试**

`backend/tests/unit/test_material_parser.py` 至少包含：

```python
def test_merge_blocks_uses_declared_precedence():
    blocks = [
        SourceBlock(source="image.png", priority=4, text="旧名称"),
        SourceBlock(source="brief.docx", priority=3, text="门户名称"),
        SourceBlock(source="user_input", priority=1, text="名称改为客户中心"),
    ]
    result = merge_source_blocks(blocks)
    assert result.blocks[0].source == "user_input"
    assert result.conflicts


def test_broken_file_becomes_visible_failure(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a pdf")
    result = parse_material(path, "application/pdf")
    assert result.status == "failed"
    assert "broken.pdf" in result.error
```

`backend/tests/integration/test_analysis_flow.py` 使用假 Agent：

```python
def test_analysis_run_returns_structured_draft(client, fake_agent, project_id):
    response = client.post(
        f"/api/v1/projects/{project_id}/analysis-runs",
        json={"supplement": "需要客户门户"},
    )
    assert response.status_code == 202
    run = client.get(f"/api/v1/runs/{response.json()['run_id']}").json()
    assert run["status"] == "succeeded"
    assert run["analysis_payload"]["requirements"][0]["source_refs"]
```

- [ ] **Step 2：运行测试，确认模型和服务尚不存在**

Run:

```powershell
Set-Location backend
python -m pytest tests/unit/test_material_parser.py tests/integration/test_analysis_flow.py -q
```

Expected: FAIL，缺少 `Material`、`GenerationRun`、解析器和分析接口。

- [ ] **Step 3：实现材料、生成记录和结构化契约**

`backend/app/schemas/requirement.py` 定义固定结构：

```python
class SourceBlock(BaseModel):
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
    suggested_project_name: str | None = None
    overview: str
    requirements: list[RequirementNode] = Field(min_length=1)
    conflicts: list[str] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)
```

`GenerationRun` 的 JSON 字段为 `analysis_payload`、`confirmed_requirements` 和 `pricing_payload`；不同任务只写自己负责的字段。

- [ ] **Step 4：实现文件存储、解析、假 Agent 边界和任务服务**

`FileStorage` 只接受项目 ID 和经过校验的扩展名：

```python
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}


class FileStorage:
    def save(self, project_id: str, original_name: str, content: bytes) -> Path:
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError("不支持的文件格式")
        project_dir = self.root / project_id / "materials"
        project_dir.mkdir(parents=True, exist_ok=True)
        target = project_dir / f"{uuid.uuid4()}{suffix}"
        target.write_bytes(content)
        return target
```

Agent 边界只暴露一个方法：

```python
class AgentGateway(Protocol):
    def analyze(self, blocks: list[SourceBlock], supplement: str | None) -> AnalysisPayload:
        raise NotImplementedError
```

`RunService.start_analysis` 创建 `pending` 记录，通过 FastAPI `BackgroundTasks` 执行；开始时改为 `running`，Pydantic 校验通过后写入 JSON 并改为 `succeeded`，异常时改为 `failed` 并保存可读错误。

- [ ] **Step 5：实现材料和任务 API，运行后端测试**

接口保持最小集合：

```text
POST   /api/v1/projects/{project_id}/materials
GET    /api/v1/projects/{project_id}/materials
DELETE /api/v1/projects/{project_id}/materials/{material_id}
POST   /api/v1/projects/{project_id}/analysis-runs
GET    /api/v1/runs/{run_id}
POST   /api/v1/runs/{run_id}/retry
PUT    /api/v1/projects/{project_id}/confirmed-requirements
```

Run:

```powershell
Set-Location backend
python -m alembic upgrade head
python -m pytest tests/unit/test_material_parser.py tests/unit/test_run_service.py tests/integration/test_analysis_flow.py -q
```

Expected: PASS；失败材料可见，分析结果符合固定 schema，确认需求后项目阶段为 `draft_ready`。

- [ ] **Step 6：实现工作台前两步**

`RequirementDraftEditor.vue` 接收并返回完整节点数组：

```typescript
defineProps<{ modelValue: RequirementNode[]; readonly?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: RequirementNode[]]; confirm: [] }>()
```

工作台第一步上传材料并启动分析，第二步轮询任务、编辑表格和确认草稿。轮询遇到 `succeeded` 或 `failed` 必须停止，组件卸载时清理定时器。

- [ ] **Step 7：验证前端并提交**

Run:

```powershell
Set-Location frontend
npm run test
npm run build
```

Expected: Vitest PASS；Vite build PASS；用户可以从材料上传进入网页草稿确认。

Commit:

```powershell
git add backend frontend
git commit -m "feat: add material analysis and editable requirement draft"
```

---

### Task 3：目标价工时分配和组合报价方案

**交付结果：** 当前角色和单价可行时生成一个推荐方案；不可行时生成最多三个组合调整方案。

**Files:**

- Create: `backend/app/schemas/pricing.py`
- Create: `backend/app/services/pricing_service.py`
- Modify: `backend/app/services/run_service.py`
- Modify: `backend/app/api/routes/runs.py`
- Create: `backend/tests/unit/test_pricing_service.py`
- Create: `backend/tests/integration/test_pricing_flow.py`
- Create: `frontend/src/types/pricing.ts`
- Modify: `frontend/src/api/runs.ts`
- Create: `frontend/src/components/PricingStep.vue`
- Modify: `frontend/src/views/ProjectWorkspaceView.vue`

**Interfaces:**

- Consumes: Task 2 的确认需求快照和 `RequirementNode.suggested_roles/complexity_weight`。
- Produces: `PricingService.allocate_current_config(target_gross_cents: int, roles: list[RoleConfig], work_packages: list[WorkPackage]) -> QuotePlan | None`。
- Produces: `PricingService.generate_adjustment_plans(target_gross_cents: int, roles: list[RoleConfig], work_packages: list[WorkPackage]) -> list[QuotePlan]`，长度不超过 3。
- Produces: `POST /api/v1/projects/{id}/pricing-runs`。
- Produces: `PUT /api/v1/projects/{id}/selected-scenario`。

- [ ] **Step 1：编写报价分配边界测试**

`backend/tests/unit/test_pricing_service.py` 固定以下行为：

```python
def test_current_config_returns_one_plan_when_target_is_reachable():
    service = PricingService()
    plans = service.build_plans(
        target_gross_cents=250_000,
        roles=[RoleConfig(name="产品", unit_price_cents=80_000, is_required=True)],
        work_packages=[WorkPackage(id="f1", role_names=["产品"], weight=1)],
    )
    assert len(plans) == 1
    assert plans[0].kind == "recommended"
    assert 242_500 <= plans[0].gross_cents <= 257_500


def test_unreachable_current_config_returns_at_most_three_adjusted_plans():
    service = PricingService()
    plans = service.build_plans(
        target_gross_cents=10_000_000,
        roles=[RoleConfig(name="产品", unit_price_cents=80_000, is_required=True)],
        work_packages=[WorkPackage(id="f1", role_names=["产品"], weight=1)],
    )
    assert 1 <= len(plans) <= 3
    assert all(plan.kind in {"adjusted", "closest"} for plan in plans)
    assert all(plan.adjustments for plan in plans)


def test_money_and_half_day_units_are_integer_based():
    totals = calculate_totals([QuoteLine(role="产品", unit_price_cents=80_000, half_day_units=3)])
    assert totals.labor_cents == 120_000
    assert totals.tax_cents == 7_200
    assert totals.gross_cents == 127_200
```

- [ ] **Step 2：运行报价测试，确认服务不存在**

Run:

```powershell
Set-Location backend
python -m pytest tests/unit/test_pricing_service.py -q
```

Expected: FAIL，缺少报价模型和 `PricingService`。

- [ ] **Step 3：定义报价模型和确定性金额计算**

`backend/app/schemas/pricing.py`：

```python
class RoleConfig(BaseModel):
    name: str
    unit_price_cents: int = Field(gt=0)
    is_required: bool = False


class WorkPackage(BaseModel):
    id: str
    role_names: list[str] = Field(min_length=1)
    weight: int = Field(ge=1, le=5)


class QuoteLine(BaseModel):
    work_package_id: str
    role: str
    unit_price_cents: int
    half_day_units: int = Field(ge=1, le=6)


class QuotePlan(BaseModel):
    id: str
    kind: Literal["recommended", "adjusted", "closest"]
    lines: list[QuoteLine]
    labor_cents: int
    tax_cents: int
    gross_cents: int
    within_target: bool
    adjustments: list[str] = Field(default_factory=list)


class QuoteTotals(BaseModel):
    labor_cents: int
    tax_cents: int
    gross_cents: int
```

金额函数使用整数和四舍五入：

```python
def half_day_cost(unit_price_cents: int, units: int) -> int:
    return (unit_price_cents * units + 1) // 2


def calculate_totals(lines: list[QuoteLine]) -> QuoteTotals:
    labor = sum(half_day_cost(line.unit_price_cents, line.half_day_units) for line in lines)
    tax = (labor * 6 + 50) // 100
    return QuoteTotals(labor_cents=labor, tax_cents=tax, gross_cents=labor + tax)


def within_target(gross_cents: int, target_gross_cents: int) -> bool:
    return target_gross_cents * 97 <= gross_cents * 100 <= target_gross_cents * 103
```

- [ ] **Step 4：实现目标价分配和组合方案**

`allocate_current_config` 使用同一确定性流程：

1. 为每个工作包和建议角色建立分配单元格。
2. 每个单元格从 1 个半天单位开始。
3. 按复杂度权重循环增加半天单位，每格最多 6 个单位。
4. 每次选择使总价更接近目标且不超过约束的增量。
5. 命中目标区间立即返回推荐方案；没有任何增量能缩小差距时返回 `None`。

组合方案固定生成三种候选后统一排序，而不是建立三套策略类：

```python
candidates = [
    self.adjust_days_and_uniform_rate(target_gross_cents, roles, work_packages),
    self.add_useful_roles_and_reallocate(target_gross_cents, roles, work_packages),
    self.closest_valid_allocation(target_gross_cents, roles, work_packages),
]
plans = [plan for plan in candidates if plan is not None]
plans.sort(key=lambda plan: (
    not plan.within_target,
    len(plan.adjustments),
    abs(plan.gross_cents - target_gross_cents),
))
return plans[:3]
```

任何候选不得新增需求工作包；新增角色只能加入 Agent 已标记为合理参与者的工作包。

- [ ] **Step 5：接入报价任务和方案选择 API**

```text
POST /api/v1/projects/{project_id}/pricing-runs
PUT  /api/v1/projects/{project_id}/selected-scenario
```

启动报价前必须存在确认需求快照。报价成功后将完整 `PricingPayload` 写入新的 `generation_run` 并把项目阶段更新为 `quote_ready`。选择方案只更新项目的 `selected_run_id` 和 `selected_scenario_id`，不得修改历史快照。

- [ ] **Step 6：运行后端报价测试**

Run:

```powershell
Set-Location backend
python -m pytest tests/unit/test_pricing_service.py tests/integration/test_pricing_flow.py -q
```

Expected: PASS；可行配置只返回一个方案，不可行配置最多返回三个带调整说明的方案。

- [ ] **Step 7：实现报价页面并验证**

`PricingStep.vue` 只负责展示方案、调整明细和单选：

```typescript
const props = defineProps<{ plans: QuotePlan[]; selectedId?: string | null }>()
const emit = defineEmits<{ select: [scenarioId: string] }>()
```

金额统一从整数分格式化，前端不得重新计算税金和总价。

Run:

```powershell
Set-Location frontend
npm run test
npm run build
```

Expected: Vitest PASS；Vite build PASS；页面可以选择推荐或组合方案。

Commit:

```powershell
git add backend frontend
git commit -m "feat: allocate target pricing and adjustment plans"
```

---

### Task 4：Office 导出、历史查看和全流程验收

**交付结果：** 用户选择方案后可以生成、下载和重新下载 Excel 与 Word；工作台可以查看历史生成记录。

**Files:**

- Create: `backend/app/models/artifact.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/services/quotation_exporter.py`
- Create: `backend/app/services/product_doc_exporter.py`
- Create: `backend/app/api/routes/artifacts.py`
- Modify: `backend/app/api/router.py`
- Create: `backend/alembic/versions/0003_create_artifacts.py`
- Create: `backend/app/templates/quotation_template.xlsx`
- Create: `backend/tests/fixtures/quotation_template.xlsx`
- Create: `backend/tests/unit/test_quotation_exporter.py`
- Create: `backend/tests/unit/test_product_doc_exporter.py`
- Create: `backend/tests/integration/test_export_and_history.py`
- Create: `frontend/src/api/artifacts.ts`
- Create: `frontend/src/components/ExportStep.vue`
- Create: `frontend/src/components/HistoryDrawer.vue`
- Modify: `frontend/src/views/ProjectWorkspaceView.vue`
- Create: `frontend/tests/e2e/presales-flow.spec.ts`
- Create: `frontend/playwright.config.ts`
- Modify: `backend/app/main.py`
- Modify: `backend/README.md`

**Interfaces:**

- Consumes: Task 3 中项目选中的生成记录和方案。
- Produces: `POST /api/v1/projects/{id}/artifacts`，同步生成两个文件。
- Produces: `GET /api/v1/projects/{id}/artifacts` 和下载接口。
- Produces: `GET /api/v1/projects/{id}/runs`，按创建时间倒序返回历史快照摘要。

- [ ] **Step 1：编写 Office 导出和历史测试**

`backend/tests/unit/test_quotation_exporter.py`：

```python
def test_exported_workbook_keeps_formula_and_print_area(tmp_path, selected_plan):
    output = tmp_path / "quote.xlsx"
    export_quotation(TEMPLATE_PATH, output, selected_plan, project_fixture())
    workbook = load_workbook(output, data_only=False)
    sheet = workbook[workbook.sheetnames[0]]
    assert sheet["J20"].value.startswith("=SUM(")
    assert sheet.print_area
    assert len(workbook.sheetnames) == 1
```

`backend/tests/unit/test_product_doc_exporter.py`：

```python
def test_product_doc_contains_confirmed_functions_and_pending_marks(tmp_path):
    output = tmp_path / "product.docx"
    export_product_doc(output, confirmed_requirements_fixture(), project_fixture())
    document = Document(output)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "项目概述" in text
    assert "功能介绍" in text
    assert "【待确认】" in text
    assert "数据库表" not in text
```

- [ ] **Step 2：运行导出测试，确认服务尚不存在**

Run:

```powershell
Set-Location backend
python -m pytest tests/unit/test_quotation_exporter.py tests/unit/test_product_doc_exporter.py -q
```

Expected: FAIL，缺少 Artifact 模型、模板和导出器。

- [ ] **Step 3：实现 Artifact 和两个导出器**

`Artifact` 字段固定为：

```python
class Artifact(Base):
    __tablename__ = "artifact"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = mapped_column(String(36), ForeignKey("project.id", ondelete="CASCADE"), nullable=False)
    generation_run_id = mapped_column(String(36), ForeignKey("generation_run.id"), nullable=False)
    artifact_type = mapped_column(String(20), nullable=False)
    version = mapped_column(Integer, nullable=False)
    file_path = mapped_column(String(500), nullable=False)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.now)
```

Excel 导出器只复制并填充确认模板，保留工作表名称、列宽、行高、合并单元格、公式、数字格式和打印区域。Word 导出器只读取确认需求快照，不调用 Agent 重新生成需求。

先在临时文件中完成导出并重新打开验证，成功后再原子移动到 `storage/{project_id}/artifacts/`，避免失败文件覆盖旧版本。

- [ ] **Step 4：实现导出、下载、历史和项目删除接口**

```text
POST   /api/v1/projects/{project_id}/artifacts
GET    /api/v1/projects/{project_id}/artifacts
GET    /api/v1/projects/{project_id}/artifacts/{artifact_id}/download
GET    /api/v1/projects/{project_id}/runs
DELETE /api/v1/projects/{project_id}
```

导出接口必须验证项目已选择方案；成功后在一个事务中写入两个 Artifact，并把项目阶段改为 `completed`。删除项目时先确认数据库对象存在，再删除关联数据库记录和 `storage/{project_id}` 目录。

- [ ] **Step 5：运行完整后端测试**

Run:

```powershell
Set-Location backend
python -m alembic upgrade head
python -m pytest -q
```

Expected: 全部 pytest PASS；导出文件可由 openpyxl 和 python-docx 重新打开；历史按时间倒序返回。

- [ ] **Step 6：实现工作台导出与历史抽屉**

`ExportStep.vue` 只展示生成按钮和两个下载项。`HistoryDrawer.vue` 展示任务类型、状态、时间、错误和关联文件，不提供版本删除按钮。

`backend/app/main.py` 在 API 路由之后挂载 `frontend/dist`：

```python
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    return FileResponse(FRONTEND_DIST / "index.html")
```

API 路由必须先注册，避免 SPA 回退吞掉 `/api/v1` 请求。

- [ ] **Step 7：编写并运行两条端到端流程**

`frontend/tests/e2e/presales-flow.spec.ts` 包含：

```typescript
test('creates project, confirms draft, selects quote and downloads artifacts', async ({ page }) => {
  await page.goto('/projects')
  await page.getByRole('button', { name: '新建项目' }).click()
  await page.getByLabel('目标报价').fill('30')
  await page.getByRole('button', { name: '创建' }).click()
  await page.getByLabel('补充说明').fill('建设客户服务门户')
  await page.getByRole('button', { name: '生成需求草稿' }).click()
  await expect(page.getByText('结构化需求草稿')).toBeVisible()
  await page.getByRole('button', { name: '确认需求' }).click()
  await page.getByRole('button', { name: '生成报价' }).click()
  await page.getByRole('radio').first().check()
  await page.getByRole('button', { name: '生成正式文件' }).click()
  await expect(page.getByRole('link', { name: '下载报价单' })).toBeVisible()
  await expect(page.getByRole('link', { name: '下载产品文档' })).toBeVisible()
})


test('shows failed background task and allows retry', async ({ page }) => {
  await page.goto('/projects/test-failure-project')
  await page.getByRole('button', { name: '生成需求草稿' }).click()
  await expect(page.getByText('生成失败')).toBeVisible()
  await expect(page.getByRole('button', { name: '重试' })).toBeVisible()
})
```

Run:

```powershell
Set-Location frontend
npm run test
npm run build
npx playwright test
```

Expected: Vitest、Vite build 和两条 Playwright 场景全部通过。

- [ ] **Step 8：最终验收并提交**

Run:

```powershell
Set-Location backend
python -m pytest -q
python -m ruff check app tests
Set-Location ..\frontend
npm run test
npm run build
npx playwright test
```

Expected: 全部命令成功；SQLite、本地文件、网页草稿、目标价报价、Excel 和 Word 完整链路可用。

Commit:

```powershell
git add backend frontend "Requirement Design.md" Plan.md docs
git commit -m "feat: complete simplified presales workflow"
```

## 最终验收清单

- [ ] 项目无需 MySQL 和 Docker 即可启动。
- [ ] 数据库只有 `project`、`material`、`generation_run`、`artifact` 四张业务表。
- [ ] 前端只有项目列表和项目工作台两个业务路由。
- [ ] 用户在网页中编辑结构化需求，不存在 Word 草稿回传路径。
- [ ] 当前配置可行时只返回一个推荐方案。
- [ ] 当前配置不可行时最多返回三个组合方案或最接近目标的结果。
- [ ] 金额和工时使用整数单位，税费计算通过边界测试。
- [ ] Excel 和 Word 可以正常打开并符合内容约束。
- [ ] 历史快照不可变，重试不会覆盖旧记录。
- [ ] 全量 pytest、Vitest、Vite build 和 Playwright 通过。
