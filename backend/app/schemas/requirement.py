"""结构化需求契约 — SourceBlock / RequirementNode / AnalysisPayload。"""

from pydantic import BaseModel, Field, model_validator


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


class ConfirmedRequirements(BaseModel):
    requirements: list[RequirementNode] = Field(min_length=1)
