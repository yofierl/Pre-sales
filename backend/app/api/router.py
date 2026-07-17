"""API 路由。"""

from fastapi import APIRouter

from app.api.routes import projects, materials, runs

router = APIRouter(prefix="/api/v1")

router.include_router(projects.router, prefix="/projects", tags=["projects"])
# materials 和 runs 路由自身包含完整路径前缀，此处直接 include
router.include_router(materials.router)
router.include_router(runs.router)
