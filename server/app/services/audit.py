from sqlalchemy.orm import Session

from app.models import OpLog, User


def log_op(db: Session, user: User, action: str, target: str = "", detail: dict | None = None) -> None:
    """随业务事务一起提交（PLAN.md 第 12 节：关键变更留痕）。"""
    db.add(
        OpLog(
            user_id=user.id if user else None,
            action=action,
            target=target,
            detail=detail,
        )
    )
