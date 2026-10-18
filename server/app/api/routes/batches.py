from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.db import get_db
from app.models import (
    STAGE_ORDER,
    AdmissionResult,
    AdmissionStatus,
    AppStatus,
    Application,
    OpLog,
    QueueEntry,
    QueueStatus,
    RecruitmentBatch,
    Role,
    Stage,
    Submission,
    User,
)
from app.schemas import BatchIn, BatchOut, BatchStatsOut, DeptStat, StageIn
from app.services.audit import log_op

router = APIRouter(prefix="/batches", tags=["batches"])


def _get_batch(batch_id: int, db: Session) -> RecruitmentBatch:
    batch = db.get(RecruitmentBatch, batch_id)
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "批次不存在")
    return batch


@router.get("", response_model=list[BatchOut])
def list_batches(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return db.query(RecruitmentBatch).order_by(RecruitmentBatch.id.desc()).all()


@router.post("", response_model=BatchOut, status_code=201)
def create_batch(
    body: BatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin)),
):
    """创建批次；activate=True 时同事务内停用其他批次（单活批次由部分唯一索引兜底）。"""
    batch = RecruitmentBatch(name=body.name, year=body.year)
    if body.activate:
        for other in db.query(RecruitmentBatch).filter(RecruitmentBatch.is_active):
            other.is_active = False
        batch.is_active = True
    db.add(batch)
    log_op(db, user, "batch.create", target=body.name, detail={"year": body.year})
    db.commit()
    db.refresh(batch)
    return batch


@router.patch("/{batch_id}/stage", response_model=BatchOut)
def change_stage(
    batch_id: int,
    body: StageIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin)),
):
    """阶段只允许逐级推进（报名→笔试→面试→录取→归档），不可跳级、不可回退。"""
    try:
        new_stage = Stage(body.stage)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "未知阶段")
    batch = _get_batch(batch_id, db)
    if STAGE_ORDER.index(new_stage) != STAGE_ORDER.index(batch.stage) + 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"当前阶段为 {batch.stage.value}，只允许推进到下一阶段",
        )
    batch.stage = new_stage
    log_op(db, user, "batch.stage", target=str(batch_id), detail={"to": new_stage.value})
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/{batch_id}/stats", response_model=BatchStatsOut)
def batch_stats(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.staff, Role.grader)),
):
    """Dashboard 单一数据源：漏斗 + 各部门进度总表（PLAN.md 第 11 节）。"""
    _get_batch(batch_id, db)

    applied = (
        db.query(func.count(Application.id))
        .filter(Application.batch_id == batch_id)
        .scalar()
    )
    submitted = (
        db.query(func.count(Submission.id))
        .join(Application, Submission.application_id == Application.id)
        .filter(Application.batch_id == batch_id)
        .scalar()
    )
    advanced = (
        db.query(func.count(Application.id))
        .filter(
            Application.batch_id == batch_id,
            Application.status == AppStatus.advanced,
        )
        .scalar()
    )
    interviewed = (
        db.query(func.count(QueueEntry.id))
        .join(Application, QueueEntry.application_id == Application.id)
        .filter(
            Application.batch_id == batch_id,
            QueueEntry.status == QueueStatus.done,
        )
        .scalar()
    )
    admitted = (
        db.query(func.count(AdmissionResult.id))
        .join(Application, AdmissionResult.application_id == Application.id)
        .filter(
            Application.batch_id == batch_id,
            AdmissionResult.status == AdmissionStatus.admitted,
            AdmissionResult.published_at.is_not(None),
        )
        .scalar()
    )

    dept_rows = (
        db.query(
            Application.dept_choice,
            func.count(Application.id),
            func.sum(case((Application.exempt_exam.is_(True), 1), else_=0)),
            func.sum(case((Application.status == AppStatus.advanced, 1), else_=0)),
        )
        .filter(Application.batch_id == batch_id)
        .group_by(Application.dept_choice)
        .all()
    )
    sub_by_dept = dict(
        db.query(Application.dept_choice, func.count(Submission.id))
        .join(Application, Submission.application_id == Application.id)
        .filter(Application.batch_id == batch_id)
        .group_by(Application.dept_choice)
        .all()
    )
    adm_by_dept = dict(
        db.query(Application.dept_choice, func.count(AdmissionResult.id))
        .join(Application, AdmissionResult.application_id == Application.id)
        .filter(
            Application.batch_id == batch_id,
            AdmissionResult.status == AdmissionStatus.admitted,
        )
        .group_by(Application.dept_choice)
        .all()
    )

    dept_stats = [
        DeptStat(
            dept=dept,
            applied=applied_n,
            exempt_exam=int(exempt_n or 0),
            submitted=sub_by_dept.get(dept, 0),
            advanced=int(advanced_n or 0),
            admitted=adm_by_dept.get(dept, 0),
        )
        for dept, applied_n, exempt_n, advanced_n in dept_rows
    ]

    return BatchStatsOut(
        batch_id=batch_id,
        funnel={
            "applied": applied,
            "submitted": submitted,
            "advanced": advanced,
            "interviewed": interviewed,
            "admitted": admitted,
        },
        dept_stats=dept_stats,
    )
