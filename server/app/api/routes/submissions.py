from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.db import get_db
from app.models import (
    Application,
    FormKind,
    FormTemplate,
    RecruitmentBatch,
    Role,
    Stage,
    Submission,
    SubStatus,
    User,
)
from app.schemas import SubmissionIn, SubmissionOut

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionOut)
def submit(
    body: SubmissionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.applicant, Role.staff, Role.admin)),
):
    """窗口期（批次 stage=exam）内可反复修改，属幂等更新；锁定后 409。
    窗口开关以服务器侧批次状态为准，不信任前端时间。
    """
    app = db.get(Application, body.application_id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "报名记录不存在")
    batch = db.get(RecruitmentBatch, app.batch_id)
    if batch.stage != Stage.exam:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"当前阶段（{batch.stage.value}）不在笔试窗口内"
        )
    if app.exempt_exam:
        raise HTTPException(status.HTTP_409_CONFLICT, "免笔试考生无需提交答卷")

    template = db.get(FormTemplate, body.template_id)
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "答卷模板不存在")
    if template.batch_id != app.batch_id or template.kind != FormKind.exam:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "模板与批次/用途不匹配")

    existing = (
        db.query(Submission)
        .filter(
            Submission.application_id == body.application_id,
            Submission.template_id == body.template_id,
        )
        .first()
    )
    if existing is not None:
        if existing.status == SubStatus.locked:
            raise HTTPException(status.HTTP_409_CONFLICT, "答卷已锁定，不可修改")
        existing.data = body.data
        existing.status = SubStatus.submitted
        db.commit()
        db.refresh(existing)
        return existing

    sub = Submission(
        application_id=body.application_id,
        template_id=body.template_id,
        data=body.data,
        status=SubStatus.submitted,
    )
    db.add(sub)
    db.commit()  # uq_submission_once 兜底并发双写
    db.refresh(sub)
    return sub


@router.get("", response_model=list[SubmissionOut])
def list_submissions(
    application_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """考生仅能查自己（约定：考生用户名 = 学号）；工作人员可查任意。"""
    app = db.get(Application, application_id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "报名记录不存在")
    if user.role == Role.applicant and app.student_no != user.username:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能查询自己的答卷")
    return db.query(Submission).filter(Submission.application_id == application_id).all()
