from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  确保模型注册到 Base.metadata
from app.api.routes import (
    answers,
    applications,
    auth,
    batches,
    forms,
    health,
    queue,
    submissions,
)
from app.core.config import get_settings
from app.core.db import Base, SessionLocal, engine

settings = get_settings()


def seed_admin() -> None:
    from app.core.security import hash_password
    from app.models import Role, User

    with SessionLocal() as db:
        if db.query(User).first() is None:
            db.add(
                User(
                    username=settings.seed_admin_username,
                    password_hash=hash_password(settings.seed_admin_password),
                    role=Role.admin,
                    display_name="管理员",
                )
            )
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 开发模式便捷通道；生产（auto_create_db=false）走 alembic upgrade head
    if settings.auto_create_db:
        Base.metadata.create_all(engine)
        seed_admin()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    health.router,
    auth.router,
    batches.router,
    answers.router,
    applications.router,
    submissions.router,
    forms.router,
    queue.router,
):
    app.include_router(r, prefix="/api")
