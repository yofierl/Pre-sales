"""项目模型 — 四阶段状态 + JSON 角色 + 整数金额。"""

import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import JSON, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectStage(str, Enum):
    INPUT = "input"
    DRAFT_READY = "draft_ready"
    QUOTE_READY = "quote_ready"
    COMPLETED = "completed"


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_gross_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quote_company: Mapped[str] = mapped_column(String(255), nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    roles_json: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False, default=ProjectStage.INPUT.value)
    selected_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    selected_scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)