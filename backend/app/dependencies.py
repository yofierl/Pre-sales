"""FastAPI 依赖注入。"""

from fastapi import Request

from app.services.openai_agent import OpenAIAgent


def get_agent_gateway(request: Request) -> OpenAIAgent:
    """返回 OpenAI Agent 实例。"""
    return OpenAIAgent()
