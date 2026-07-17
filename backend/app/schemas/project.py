"""项目 Pydantic schemas — 整数金额、JSON 角色。"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ProjectStage(str, Enum):
    INPUT = "input"
    DRAFT_READY = "draft_ready"
    QUOTE_READY = "quote_ready"
    COMPLETED = "completed"


class ProjectType(str, Enum):
    NEW = "new"
    LEGACY = "legacy"


class RoleConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    unit_price_cents: int = Field(..., gt=0)
    is_required: bool = False


class ProjectCreate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    project_type: ProjectType
    target_price_wan: str
    quote_company: str = "重庆酷小贝软件开发有限公司"
    quote_date: date
    customer_name: str | None = None
    roles: list[RoleConfig] = []

    @field_validator("target_price_wan")
    @classmethod
    def must_be_positive(cls, v: str) -> str:
        try:
            if Decimal(v) <= 0:
                raise ValueError
        except Exception:
            raise ValueError("目标报价必须大于 0")
        return v


class ProjectUpdate(BaseModel):
    name: str | None = None
    project_type: ProjectType | None = None
    target_price_wan: str | None = None
    quote_company: str | None = None
    quote_date: date | None = None
    customer_name: str | None = None
    stage: str | None = None  # explicitly rejected


class RoleConfigResponse(BaseModel):
    name: str
    unit_price_cents: int
    is_required: bool


class ProjectResponse(BaseModel):
    id: str
    name: str | None
    project_type: str
    target_gross_cents: int
    quote_company: str
    quote_date: date
    customer_name: str | None
    roles: list[RoleConfigResponse]
    stage: str
    selected_run_id: str | None
    selected_scenario_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int = 1
    page_size: int = 20