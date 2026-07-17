"""材料 CRUD API。"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.material import Material
from app.models.project import Project
from app.schemas.material import MaterialResponse, MaterialListResponse
from app.services.file_storage import FileStorage

router = APIRouter(prefix="/projects/{project_id}/materials", tags=["materials"])


def _get_project(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.post("", response_model=MaterialResponse, status_code=201)
def upload_material(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _get_project(project_id, db)
    storage = FileStorage()
    content = file.file.read()
    try:
        stored_path = storage.save(project_id, file.filename or "unnamed", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    material = Material(
        project_id=project_id,
        original_name=file.filename or "unnamed",
        stored_path=str(stored_path),
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.get("", response_model=MaterialListResponse)
def list_materials(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    items = db.query(Material).filter(Material.project_id == project_id).order_by(Material.created_at.desc()).all()
    return MaterialListResponse(items=items, total=len(items))


@router.delete("/{material_id}", status_code=204)
def delete_material(project_id: str, material_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    material = db.query(Material).filter(Material.id == material_id, Material.project_id == project_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="材料不存在")
    import os
    if os.path.exists(material.stored_path):
        os.remove(material.stored_path)
    db.delete(material)
    db.commit()
