import os
import pathlib

# 必须在导入 app 之前设定环境，engine 在导入期绑定
TEST_DB = pathlib.Path(__file__).parent / "test.db"
os.environ["YUNA_DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["YUNA_AUTO_CREATE_DB"] = "true"
os.environ["YUNA_JWT_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
if TEST_DB.exists():
    TEST_DB.unlink()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # 进入 lifespan：建表 + 播种 admin
        yield c


@pytest.fixture(scope="session")
def admin_headers(client):
    r = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def register_and_login(client, username: str) -> dict:
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": "pass123456", "display_name": username},
    )
    assert r.status_code == 201
    r = client.post(
        "/api/auth/login", json={"username": username, "password": "pass123456"}
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
