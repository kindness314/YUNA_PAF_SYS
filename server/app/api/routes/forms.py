from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.db import get_db
from app.models import FormKind, FormTemplate, RecruitmentBatch, Role, User
from app.schemas import FormSchemaIn, FormTemplateOut
from app.services.audit import log_op

router = APIRouter(prefix="/forms", tags=["forms"])


def _parse_kind(kind: str) -> FormKind:
    try:
        return FormKind(kind)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板类型不存在")


@router.get("/{batch_id}/{kind}", response_model=FormTemplateOut)
def get_latest(
    batch_id: int,
    kind: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """取最新版本模板（form-create rule JSON），考生端与管理端同源。"""
    _parse_kind(kind)
    latest = (
        db.query(FormTemplate)
        .filter(FormTemplate.batch_id == batch_id, FormTemplate.kind == FormKind(kind))
        .order_by(FormTemplate.version.desc())
        .first()
    )
    if latest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "尚未发布模板")
    return latest


@router.put("/{batch_id}/{kind}", response_model=FormTemplateOut)
def save(
    batch_id: int,
    kind: str,
    body: FormSchemaIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin)),
):
    """保存即新版本（版本号自增），历史版本保留可回溯。"""
    _parse_kind(kind)
    if db.get(RecruitmentBatch, batch_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "批次不存在")
    latest = (
        db.query(FormTemplate)
        .filter(FormTemplate.batch_id == batch_id, FormTemplate.kind == FormKind(kind))
        .order_by(FormTemplate.version.desc())
        .first()
    )
    template = FormTemplate(
        batch_id=batch_id,
        kind=FormKind(kind),
        name=body.name,
        schema_json=body.form_schema,
        version=(latest.version + 1) if latest else 1,
        updated_by=user.id,
    )
    db.add(template)
    log_op(db, user, "form.save", target=f"{batch_id}/{kind}", detail={"version": template.version})
    db.commit()
    db.refresh(template)
    return template
