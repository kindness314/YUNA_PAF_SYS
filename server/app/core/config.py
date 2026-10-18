from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """环境变量前缀 YUNA_，如 YUNA_DATABASE_URL。详见根目录 .env.example。"""

    model_config = SettingsConfigDict(env_prefix="YUNA_", env_file=".env", extra="ignore")

    app_name: str = "YUNA PAF 招新系统"
    debug: bool = True

    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    jwt_secret: str = "dev-insecure-secret-change-me-0123456789abcdef"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    # 开发模式：启动时 create_all 并播种 admin；生产置 false，用 alembic upgrade head
    auto_create_db: bool = True
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123456"

    upload_dir: str = "./uploads"
    upload_max_mb: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
