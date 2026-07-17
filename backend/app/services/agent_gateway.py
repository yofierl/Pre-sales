"""Agent 网关 — 与 AI 模型的交互边界。

当前为 FakeAgent 实现，后续可替换为真实 OpenAI 调用。"""

from typing import Protocol

from app.schemas.requirement import AnalysisPayload, SourceBlock


class AgentGateway(Protocol):
    """Agent 网关协议 — 只定义分析接口。"""

    def analyze(self, blocks: list[SourceBlock], supplement: str | None = None) -> AnalysisPayload:
        """分析来源块并返回结构化需求。"""
        ...


class FakeAgent:
    """假 Agent — 返回固定结果用于测试和开发。"""

    def analyze(self, blocks: list[SourceBlock], supplement: str | None = None) -> AnalysisPayload:
        return AnalysisPayload(
            suggested_project_name="客户门户",
            overview="客户管理门户开发项目",
            requirements=[
                {
                    "id": "r1",
                    "module": "客户管理",
                    "feature": "用户登录",
                    "description": "支持手机号和邮箱登录",
                    "source_refs": [b.source for b in blocks] if blocks else ["user_input"],
                    "complexity_weight": 2,
                    "suggested_roles": ["后端"],
                },
                {
                    "id": "r2",
                    "module": "客户管理",
                    "feature": "权限管理",
                    "description": "支持角色管理和权限分配",
                    "source_refs": [b.source for b in blocks] if blocks else ["user_input"],
                    "complexity_weight": 3,
                    "suggested_roles": ["后端", "前端"],
                    "system_added": True,
                },
            ],
            conflicts=[],
            unanswered_questions=[],
        )
