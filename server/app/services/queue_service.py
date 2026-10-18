"""面试队列核心操作 —— PLAN.md 第 12 节一致性模式的参考实现。

- 发号：组计数器 UPDATE ... RETURNING 原子自增，不依赖 Redis。
- 叫号：先 SELECT 最小待叫号，再条件 UPDATE（WHERE status='候考'），
  rowcount=0 说明被并发抢走，重试下一个——两个面试官同时叫号不会
  叫走同一个人。
- 完成：条件 UPDATE（面试中 → 已完成），重复完成返回 False。

注意：本模块被 async 路由直接调用（SQLite/本地 PG 延迟可忽略），
bus.publish 与事件循环同线程，天然线程安全。
"""
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import InterviewGroup, QueueEntry, QueueStatus
from app.services.events import publish_group_event


def checkin(db: Session, group_id: int, application_id: int) -> QueueEntry:
    """签到发号。重复签到由 queue_entries.application_id 唯一约束兜底。"""
    res = db.execute(
        update(InterviewGroup)
        .where(InterviewGroup.id == group_id)
        .values(seq=InterviewGroup.seq + 1)
        .returning(InterviewGroup.seq)
    )
    seq = res.scalar_one_or_none()
    if seq is None:
        raise ValueError("面试组不存在")
    entry = QueueEntry(group_id=group_id, application_id=application_id, seq=seq)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("该考生已签到")
    publish_group_event(group_id)
    db.refresh(entry)
    return entry


def call_next(db: Session, group_id: int, room: str) -> QueueEntry | None:
    """叫下一位。无人可叫返回 None。"""
    for _ in range(5):  # 并发竞争下最多重试 5 个候选
        entry_id = db.execute(
            select(QueueEntry.id)
            .where(
                QueueEntry.group_id == group_id,
                QueueEntry.status == QueueStatus.waiting,
            )
            .order_by(QueueEntry.seq)
            .limit(1)
        ).scalar_one_or_none()
        if entry_id is None:
            return None
        res = db.execute(
            update(QueueEntry)
            .where(
                QueueEntry.id == entry_id,
                QueueEntry.status == QueueStatus.waiting,
            )
            .values(
                status=QueueStatus.interviewing,
                room=room,
                called_at=func.now(),
            )
        )
        if res.rowcount == 1:
            db.commit()
            publish_group_event(group_id)
            return db.get(QueueEntry, entry_id)
    return None


def finish(db: Session, entry_id: int) -> bool:
    """面试完成。非'面试中'状态（重复完成/未叫号）返回 False。"""
    res = db.execute(
        update(QueueEntry)
        .where(
            QueueEntry.id == entry_id,
            QueueEntry.status == QueueStatus.interviewing,
        )
        .values(status=QueueStatus.done, finished_at=func.now())
    )
    db.commit()
    if res.rowcount != 1:
        return False
    entry = db.get(QueueEntry, entry_id)
    if entry is not None:
        publish_group_event(entry.group_id)
    return True
