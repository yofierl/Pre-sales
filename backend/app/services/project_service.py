"""项目服务 — 直接使用 SQLAlchemy 模型，不设仓储层。"""

from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStage
from app.schemas.project import ProjectCreate, ProjectUpdate, RoleConfig

DEFAULT_ROLES = [
    {"name": "产品", "unit_price_cents": 80_000, "is_required": True},
    {"name": "前端", "unit_price_cents": 85_000, "is_required": False},
    {"name": "后端", "unit_price_cents": 85_000, "is_required": False},
    {"name": "测试", "unit_price_cents": 75_000, "is_required": True},
]


def wan_to_cents(value: Decimal) -> int:
    return int((value * Decimal("1_000_000")).quantize(Decimal("1")))


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: ProjectCreate) -> Project:
        roles = [r.model_dump() for r in data.roles] if data.roles else DEFAULT_ROLES
        role_names = {r["name"] for r in roles}
        if not {"产品", "测试"}.issubset(role_names):
            raise ValueError("产品和测试角色不可删除")

        project = Project(
            name=data.name,
            project_type=data.project_type.value,
            target_gross_cents=wan_to_cents(Decimal(data.target_price_wan)),
            quote_company=data.quote_company,
            quote_date=data.quote_date,
            customer_name=data.customer_name,
            roles_json=roles,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get(self, project_id: str) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list(self, page: int = 1, page_size: int = 20) -> tuple[list[Project], int]:
        query = self.db.query(Project)
        total = query.count()
        items = query.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, project_id: str, data: ProjectUpdate) -> Project | None:
        project = self.get(project_id)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude={"stage"})
        if "target_price_wan" in update_data:
            update_data["target_gross_cents"] = wan_to_cents(Decimal(update_data.pop("target_price_wan")))

        for field, value in update_data.items():
            setattr(project, field, value)

        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project_id: str) -> bool:
        project = self.get(project_id)
        if not project:
            return False
        self.db.delete(project)
        self.db.commit()
        return True
