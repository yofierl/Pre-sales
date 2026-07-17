"""API 路由。"""

from fastapi import APIRouter

from app.api.routes import projects

router = APIRouter(prefix="/api/v1")

router.include_router(projects.router, prefix="/projects", tags=["projects"])