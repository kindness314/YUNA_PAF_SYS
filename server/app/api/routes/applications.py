from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.db import get_db
from app.models import (
    AppSource,
    Application,
    RecruitmentBatch,
    Role,
    Stage,
    User,
)
from app.schemas import ApplicationIn, ApplicationOut
from app.services.audit import log_op

router = APIRouter(prefix="/applications", tags=["applications"])

# 阶段规则：线上报名仅报名期；现场临时报名放宽到面试日当天（PLAN.md 第 12 节）
ONSITE_ALLOWED_STAGES = {Stage.registration, Stage.interview}


@router.post("", response_model=ApplicationOut, status_code=201)
def apply(
    body: ApplicationIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.applicant, Role.staff, Role.admin)),
):
    batch = db.get(RecruitmentBatch, body.batch_id)
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "批次不存在")
    if not batch.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "批次未开启")

    try:
        source = AppSource(body.source)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "source 取值非法")

    if source == AppSource.online and batch.stage != Stage.registration:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"当前阶段（{batch.stage.value}）已停止线上报名"
        )
    if source == AppSource.onsite:
        if batch.stage not in ONSITE_ALLOWED_STAGES:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"当前阶段（{batch.stage.value}）不可临时报名"
            )
        if user.role == Role.applicant:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "临时报名由现场工作人员录入")

    if user.role == Role.applicant:
        # 自助报名的身份和免试资格不能由请求体自行指定。
        if body.student_no != user.username:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "只能使用本人学号报名")
        if body.exempt_exam:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "免笔试资格由工作人员设置")

    dup = (
        db.query(Application)
        .filter(
            Application.batch_id == body.batch_id,
            Application.student_no == body.student_no,
        )
        .first()
    )
    if dup is not None:
        # 幂等语义：重复报名返回既有记录标识，由数据库唯一约束兜底
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"message": "该学号已报名", "application_id": dup.id},
        )

    app = Application(
        batch_id=body.batch_id,
        student_no=body.student_no,
        name=body.name,
        phone=body.phone,
        dept_choice=body.dept_choice,
        source=source,
        exempt_exam=body.exempt_exam,
        extra=body.extra,
    )
    db.add(app)
    log_op(db, user, "application.create", target=body.student_no)
    db.commit()
    db.refresh(app)
    return app


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    batch_id: int,
    dept: str | None = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.staff, Role.grader)),
):
    q = db.query(Application).filter(Application.batch_id == batch_id)
    if dept:
        q = q.filter(Application.dept_choice == dept)
    return (
        q.order_by(Application.id.desc())
        .offset((max(page, 1) - 1) * size)
        .limit(min(size, 100))
        .all()
    )

@router.get("/mine", response_model=ApplicationOut)
def my_application(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.applicant, Role.staff, Role.admin)),
):
    """考生自查报名记录（约定：考生用户名 = 学号）。"""
    app = (
        db.query(Application)
        .filter(
            Application.batch_id == batch_id,
            Application.student_no == user.username,
        )
        .first()
    )
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "尚未报名")
    return app
