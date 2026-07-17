"""生成任务相关 Pydantic schemas。"""

from datetime import datetime

from pydantic import BaseModel


class RunCreate(BaseModel):
    supplement: str | None = None


class RunResponse(BaseModel):
    id: str
    project_id: str
    task_type: str
    status: str
    error_message: str | None = None
    analysis_payload: dict | None = None
    confirmed_requirements: dict | None = None
    pricing_payload: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunListResponse(BaseModel):
    items: list[RunResponse]
    total: int
