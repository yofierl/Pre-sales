"""材料相关 Pydantic schemas。"""

from datetime import datetime

from pydantic import BaseModel


class MaterialResponse(BaseModel):
    id: str
    project_id: str
    original_name: str
    file_size: int
    mime_type: str
    parse_status: str
    parse_error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialListResponse(BaseModel):
    items: list[MaterialResponse]
    total: int
