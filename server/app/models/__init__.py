"""领域模型。一致性约束按 PLAN.md 第 12 节下沉到数据库：
唯一约束、CHECK、条件更新；派生数据（均分/统计）不落列。
"""
import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, JSONField


class Role(str, enum.Enum):
    admin = "admin"            # 管理员
    grader = "grader"          # 阅卷员
    staff = "staff"            # 现场签到员
    interviewer = "interviewer"  # 面试官
    applicant = "applicant"    # 考生


class Stage(str, enum.Enum):
    registration = "registration"  # 报名中
    exam = "exam"                  # 笔试窗口
    interview = "interview"        # 面试阶段
    admission = "admission"        # 录取发布
    closed = "closed"              # 归档


STAGE_ORDER = [Stage.registration, Stage.exam, Stage.interview, Stage.admission, Stage.closed]


class FormKind(str, enum.Enum):
    application = "application"  # 报名表单
    exam = "exam"                # 笔试答卷模板


class AppSource(str, enum.Enum):
    online = "online"  # 线上报名
    onsite = "onsite"  # 临时报名（现场）


class AppStatus(str, enum.Enum):
    submitted = "submitted"    # 已报名
    advanced = "advanced"      # 达线进面
    rejected = "rejected"      # 未进面


class SubStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    locked = "locked"  # 阅卷开始后锁定


class QueueStatus(str, enum.Enum):
    waiting = "waiting"          # 候考
    interviewing = "interviewing"  # 面试中
    done = "done"                # 已完成
    skipped = "skipped"          # 过号
    absent = "absent"            # 缺考


class AdmissionStatus(str, enum.Enum):
    admitted = "admitted"  # 拟录取
    waitlist = "waitlist"  # 候补
    rejected = "rejected"  # 淘汰


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, native_enum=False, length=16), default=Role.applicant
    )
    display_name: Mapped[str] = mapped_column(String(64), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RecruitmentBatch(Base):
    __tablename__ = "recruitment_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    year: Mapped[int] = mapped_column(Integer)
    stage: Mapped[Stage] = mapped_column(
        SAEnum(Stage, native_enum=False, length=16), default=Stage.registration
    )
    # 全局仅一个进行中的批次（部分唯一索引，SQLite/PG 均生效）
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("year", "name", name="uq_batch_year_name"),
        Index(
            "uq_single_active_batch",
            "is_active",
            unique=True,
            sqlite_where=text("is_active"),
            postgresql_where=text("is_active"),
        ),
    )


class FormTemplate(Base):
    __tablename__ = "form_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("recruitment_batches.id"), index=True)
    kind: Mapped[FormKind] = mapped_column(SAEnum(FormKind, native_enum=False, length=16))
    name: Mapped[str] = mapped_column(String(128), default="")
    schema_json: Mapped[dict] = mapped_column(JSONField, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("batch_id", "kind", "version", name="uq_template_version"),
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("recruitment_batches.id"), index=True
    )
    # 学号每批次唯一 —— 重复报名由数据库兜底
    student_no: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(20))
    dept_choice: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[AppSource] = mapped_column(
        SAEnum(AppSource, native_enum=False, length=16), default=AppSource.online
    )
    exempt_exam: Mapped[bool] = mapped_column(Boolean, default=False)  # 免笔试标记
    extra: Mapped[dict] = mapped_column(JSONField, default=dict)  # form-create 动态答案
    status: Mapped[AppStatus] = mapped_column(
        SAEnum(AppStatus, native_enum=False, length=16), default=AppStatus.submitted
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("batch_id", "student_no", name="uq_application_batch_student"),
        CheckConstraint("length(student_no) > 0", name="ck_application_student_no"),
    )


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    template_id: Mapped[int] = mapped_column(ForeignKey("form_templates.id"))
    data: Mapped[dict] = mapped_column(JSONField, default=dict)
    status: Mapped[SubStatus] = mapped_column(
        SAEnum(SubStatus, native_enum=False, length=16), default=SubStatus.submitted
    )
    submitted_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 一人一卷：重复交卷由唯一约束兜底，业务层做幂等更新
    __table_args__ = (
        UniqueConstraint("application_id", "template_id", name="uq_submission_once"),
    )


class InterviewGroup(Base):
    __tablename__ = "interview_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("recruitment_batches.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    seq: Mapped[int] = mapped_column(Integer, default=0)  # 组内发号计数器（原子自增）
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("batch_id", "name", name="uq_group_batch_name"),
    )


class QueueEntry(Base):
    __tablename__ = "queue_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("interview_groups.id"), index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    seq: Mapped[int] = mapped_column(Integer)
    status: Mapped[QueueStatus] = mapped_column(
        SAEnum(QueueStatus, native_enum=False, length=16), default=QueueStatus.waiting
    )
    room: Mapped[str | None] = mapped_column(String(32))
    called_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("seq >= 1", name="ck_queue_seq_positive"),
    )


class InterviewScore(Base):
    __tablename__ = "interview_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    queue_entry_id: Mapped[int] = mapped_column(
        ForeignKey("queue_entries.id"), index=True
    )
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    dimensions: Mapped[dict] = mapped_column(JSONField, default=dict)
    total: Mapped[float] = mapped_column(Numeric(5, 2))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 一位面试官对一名考生仅一条评分；重复提交走 upsert
    __table_args__ = (
        UniqueConstraint("queue_entry_id", "interviewer_id", name="uq_score_once"),
        CheckConstraint("total >= 0 AND total <= 100", name="ck_score_range"),
    )


class AdmissionResult(Base):
    __tablename__ = "admission_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id"), unique=True
    )
    status: Mapped[AdmissionStatus] = mapped_column(
        SAEnum(AdmissionStatus, native_enum=False, length=16)
    )
    note: Mapped[str] = mapped_column(String(255), default="")
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class OpLog(Base):
    __tablename__ = "op_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[dict | None] = mapped_column(JSONField)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
