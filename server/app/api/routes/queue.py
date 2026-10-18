import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.db import get_db
from app.models import (
    Application,
    InterviewGroup,
    QueueEntry,
    RecruitmentBatch,
    Role,
    Stage,
    User,
)
from app.schemas import CallIn, CheckinIn, GroupIn, GroupOut, QueueEntryOut
from app.services import queue_service
from app.services.events import bus
from app.services.audit import log_op

router = APIRouter(prefix="/queue", tags=["queue"])


@router.post("/groups", response_model=GroupOut, status_code=201)
def create_group(
    body: GroupIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin)),
):
    if db.get(RecruitmentBatch, body.batch_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "批次不存在")
    if (
        db.query(InterviewGroup)
        .filter(
            InterviewGroup.batch_id == body.batch_id,
            InterviewGroup.name == body.name,
        )
        .first()
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "同名面试组已存在")
    group = InterviewGroup(batch_id=body.batch_id, name=body.name)
    db.add(group)
    log_op(db, user, "queue.group.create", target=body.name)
    db.commit()
    db.refresh(group)
    return group


@router.get("/groups", response_model=list[GroupOut])
def list_groups(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(InterviewGroup)
        .filter(InterviewGroup.batch_id == batch_id)
        .order_by(InterviewGroup.id)
        .all()
    )


@router.post("/checkin", response_model=QueueEntryOut, status_code=201)
async def checkin(
    body: CheckinIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.staff, Role.admin)),
):
    app = db.get(Application, body.application_id)
    if app is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "报名记录不存在")
    batch = db.get(RecruitmentBatch, app.batch_id)
    if batch.stage != Stage.interview:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"当前阶段（{batch.stage.value}）不在面试日"
        )
    group = db.get(InterviewGroup, body.group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "面试组不存在")
    if group.batch_id != app.batch_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "考生与面试组不属于同一批次")
    try:
        entry = queue_service.checkin(db, body.group_id, body.application_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    log_op(db, user, "queue.checkin", target=str(entry.application_id), detail={"seq": entry.seq})
    db.commit()
    return entry


@router.post("/groups/{group_id}/call", response_model=QueueEntryOut)
async def call_next(
    group_id: int,
    body: CallIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.interviewer, Role.admin)),
):
    """叫下一位；队列空返回 204。并发叫号由条件更新保证不重复（第 12 节）。"""
    if db.get(InterviewGroup, group_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "面试组不存在")
    entry = queue_service.call_next(db, group_id, body.room)
    if entry is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return entry


@router.post("/entries/{entry_id}/finish")
async def finish_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.interviewer, Role.admin)),
):
    ok = queue_service.finish(db, entry_id)
    if not ok:
        raise HTTPException(status.HTTP_409_CONFLICT, "该队列项不在面试中状态")
    return {"ok": True}


@router.get("/groups/{group_id}/entries", response_model=list[QueueEntryOut])
def list_entries(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return (
        db.query(QueueEntry)
        .filter(QueueEntry.group_id == group_id)
        .order_by(QueueEntry.seq)
        .all()
    )


@router.get("/groups/{group_id}/events")
async def stream_events(
    group_id: int,
    user: User = Depends(get_current_user),
):
    """叫号大屏/看板 SSE 通道：事件只发"refresh"信号，客户端收到后重拉列表。"""

    async def gen():
        q = bus.subscribe(group_id)
        try:
            yield "retry: 3000\n\n"
            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            bus.unsubscribe(group_id, q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
