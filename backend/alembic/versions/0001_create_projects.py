"""创建 project 表（SQLite + 整数金额 + JSON 角色）。"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("project_type", sa.String(20), nullable=False),
        sa.Column("target_gross_cents", sa.Integer(), nullable=False),
        sa.Column("quote_company", sa.String(255), nullable=False),
        sa.Column("quote_date", sa.Date(), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("roles_json", sa.JSON(), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False, server_default="input"),
        sa.Column("selected_run_id", sa.String(36), nullable=True),
        sa.Column("selected_scenario_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_project_stage", "project", ["stage"])
    op.create_index("ix_project_created_at", "project", ["created_at"])


def downgrade() -> None:
    op.drop_table("project")