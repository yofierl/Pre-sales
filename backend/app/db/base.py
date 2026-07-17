"""SQLAlchemy 基础配置。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类。"""

    pass