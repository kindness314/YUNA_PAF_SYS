"""进程内 SSE 事件总线。

一致性约定（PLAN.md 第 12 节）：事件只作为"该刷新了"的信号，
不承载权威数据；客户端收到后重拉 DB。进程重启即丢连接属预期——
客户端 retry 后重连并全量拉取，天然对账。
"""
import asyncio
from collections import defaultdict

from app.models import InterviewGroup

Key = int  # group_id


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[Key, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, key: Key) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        self._subs[key].add(q)
        return q

    def unsubscribe(self, key: Key, q: asyncio.Queue) -> None:
        self._subs[key].discard(q)
        if not self._subs[key]:
            self._subs.pop(key, None)

    def publish(self, key: Key, data: dict) -> None:
        for q in list(self._subs.get(key, ())):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass  # 慢消费者靠轮询兜底，不阻塞广播


bus = EventBus()


def publish_group_event(group_id: int) -> None:
    bus.publish(group_id, {"type": "refresh", "group_id": group_id})
