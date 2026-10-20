import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.db import get_db
from app.models import ExamAnswer, RecruitmentBatch, Role, User
from app.schemas import ExamAnswerIn, ExamAnswerOut
from app.services.audit import log_op

router = APIRouter(prefix="/batches", tags=["exam-answer"])


@router.get("/{batch_id}/exam-answer", response_model=ExamAnswerOut)
def get_answer(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """管理端随时可读；考生在发布前一律 404（不暴露是否已有草稿）。"""
    row = db.query(ExamAnswer).filter(ExamAnswer.batch_id == batch_id).first()
    if row is None or (not row.published and user.role == Role.applicant):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "解析尚未发布")
    return row


@router.put("/{batch_id}/exam-answer", response_model=ExamAnswerOut)
def save_answer(
    batch_id: int,
    body: ExamAnswerIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin)),
):
    """upsert：每批次一份解析；发布时间仅记录首次发布时刻。"""
    if db.get(RecruitmentBatch, batch_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "批次不存在")
    row = db.query(ExamAnswer).filter(ExamAnswer.batch_id == batch_id).first()
    if row is None:
        row = ExamAnswer(batch_id=batch_id)
        db.add(row)
    row.content = body.content
    if body.published and not row.published:
        row.published_at = dt.datetime.now(dt.timezone.utc)
    elif not body.published:
        row.published_at = None
    row.published = body.published
    row.updated_by = user.id
    log_op(db, user, "exam_answer.save", target=str(batch_id), detail={"published": body.published})
    db.commit()
    db.refresh(row)
    return row
