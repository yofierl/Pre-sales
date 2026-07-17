"""文件存储服务 — 本地目录保存上传文件。"""

import uuid
from pathlib import Path

from app.core.config import settings


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}


class FileStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.storage_root

    def save(self, project_id: str, original_name: str, content: bytes) -> Path:
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {suffix}")
        project_dir = self.root / project_id / "materials"
        project_dir.mkdir(parents=True, exist_ok=True)
        target = project_dir / f"{uuid.uuid4()}{suffix}"
        target.write_bytes(content)
        return target

    def get_path(self, project_id: str, stored_path: str) -> Path | None:
        p = Path(stored_path)
        if p.exists():
            return p
        return None

    def delete_project_dir(self, project_id: str) -> None:
        project_dir = self.root / project_id
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
