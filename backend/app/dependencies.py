"""FastAPI 依赖注入。"""

from fastapi import Request

from app.services.agent_gateway import FakeAgent


def get_agent_gateway(request: Request) -> FakeAgent:
    """返回 Agent 网关实例。"""
    return FakeAgent()
