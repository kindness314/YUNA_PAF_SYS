"""覆盖 PLAN.md 第 12 节的一致性验收：重复报名、幂等交卷、并发叫号、
重复完成、阶段越权。"""
from conftest import register_and_login

ADMIN_CREDS = {"username": "admin", "password": "admin123456"}


def new_batch(client, admin_headers, name: str) -> dict:
    r = client.post(
        "/api/batches", json={"name": name, "year": 2026}, headers=admin_headers
    )
    assert r.status_code == 201
    return r.json()


def advance(client, admin_headers, batch_id: int, to: str) -> dict:
    r = client.patch(
        f"/api/batches/{batch_id}/stage", json={"stage": to}, headers=admin_headers
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_admin_login_me(client):
    r = client.post("/api/auth/login", json=ADMIN_CREDS)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["role"] == "admin"


def test_register_conflict_and_rbac(client):
    assert client.post("/api/auth/register", json={
        "username": "stu0001", "password": "pass123456"
    }).status_code == 201
    assert client.post("/api/auth/register", json={
        "username": "stu0001", "password": "pass123456"
    }).status_code == 409
    # 未登录禁入
    assert client.get("/api/batches").status_code == 401
    # 考生无统计权限
    h = register_and_login(client, "stu0002")
    r = client.post("/api/batches", json={"name": "x", "year": 2026}, headers=h)
    assert r.status_code == 403


def test_flow_registration_and_idempotent_submission(client, admin_headers):
    batch = new_batch(client, admin_headers, "2026秋-流程批")
    h = register_and_login(client, "20261001")

    a1 = client.post("/api/applications", json={
        "batch_id": batch["id"], "student_no": "20261001", "name": "李四",
        "phone": "13800000001", "dept_choice": "技术部",
    }, headers=h)
    assert a1.status_code == 201
    # 学号重复 → 409 且带既有记录 ID（幂等语义）
    dup = client.post("/api/applications", json={
        "batch_id": batch["id"], "student_no": "20261001", "name": "李四",
        "phone": "13800000001", "dept_choice": "技术部",
    }, headers=h)
    assert dup.status_code == 409
    assert dup.json()["detail"]["application_id"] == a1.json()["id"]
    mine = client.get("/api/applications/mine", params={"batch_id": batch["id"]}, headers=h)
    assert mine.status_code == 200 and mine.json()["id"] == a1.json()["id"]

    # 阶段不可跳级
    assert client.patch(
        f"/api/batches/{batch['id']}/stage", json={"stage": "interview"},
        headers=admin_headers,
    ).status_code == 400

    advance(client, admin_headers, batch["id"], "exam")
    # 报名期已过，线上报名拒绝
    assert client.post("/api/applications", json={
        "batch_id": batch["id"], "student_no": "20261002", "name": "王五",
        "phone": "13800000002", "dept_choice": "技术部",
    }, headers=h).status_code == 409

    t = client.put(f"/api/forms/{batch['id']}/exam", json={
        "name": "笔试卷A", "schema_json": {"rule": [{"field": "q1", "type": "input"}]},
    }, headers=admin_headers).json()
    assert t["version"] == 1
    # 再存即 v2
    t2 = client.put(f"/api/forms/{batch['id']}/exam", json={
        "name": "笔试卷A", "schema_json": {"rule": []},
    }, headers=admin_headers).json()
    assert t2["version"] == 2

    s1 = client.post("/api/submissions", json={
        "application_id": a1.json()["id"], "template_id": t2["id"], "data": {"q1": "ans1"},
    }, headers=h)
    assert s1.status_code == 200
    # 幂等更新：重复提交同一答卷 → 同一 ID，数据覆盖
    s2 = client.post("/api/submissions", json={
        "application_id": a1.json()["id"], "template_id": t2["id"], "data": {"q1": "ans2"},
    }, headers=h)
    assert s2.status_code == 200
    assert s2.json()["id"] == s1.json()["id"]

    stats = client.get(f"/api/batches/{batch['id']}/stats", headers=admin_headers).json()
    assert stats["funnel"] == {
        "applied": 1, "submitted": 1, "advanced": 0, "interviewed": 0, "admitted": 0,
    }
    assert stats["dept_stats"][0]["dept"] == "技术部"


def test_interview_queue_consistency(client, admin_headers):
    batch = new_batch(client, admin_headers, "2026秋-面试批")
    h = register_and_login(client, "20262001")
    app = client.post("/api/applications", json={
        "batch_id": batch["id"], "student_no": "20262001", "name": "赵六",
        "phone": "13800000003", "dept_choice": "技术部",
    }, headers=h).json()

    group = client.post("/api/queue/groups", json={
        "batch_id": batch["id"], "name": "技术组A",
    }, headers=admin_headers).json()

    # 非面试日签到拒绝
    assert client.post("/api/queue/checkin", json={
        "group_id": group["id"], "application_id": app["id"],
    }, headers=admin_headers).status_code == 409

    advance(client, admin_headers, batch["id"], "exam")
    advance(client, admin_headers, batch["id"], "interview")

    e1 = client.post("/api/queue/checkin", json={
        "group_id": group["id"], "application_id": app["id"],
    }, headers=admin_headers)
    assert e1.status_code == 201
    assert e1.json()["seq"] == 1
    # 重复签到 → 409（唯一约束兜底）
    assert client.post("/api/queue/checkin", json={
        "group_id": group["id"], "application_id": app["id"],
    }, headers=admin_headers).status_code == 409

    # 叫号 → 面试中；再叫 → 队列空 204；重复 finish → 409
    c1 = client.post(f"/api/queue/groups/{group['id']}/call", json={"room": "1号房"}, headers=admin_headers)
    assert c1.status_code == 200 and c1.json()["status"] == "interviewing"
    c2 = client.post(f"/api/queue/groups/{group['id']}/call", json={"room": "1号房"}, headers=admin_headers)
    assert c2.status_code == 204
    assert client.post(f"/api/queue/entries/{e1.json()['id']}/finish", headers=admin_headers).status_code == 200
    assert client.post(f"/api/queue/entries/{e1.json()['id']}/finish", headers=admin_headers).status_code == 409

    entries = client.get(f"/api/queue/groups/{group['id']}/entries", headers=admin_headers).json()
    assert entries[0]["status"] == "done"


def test_exam_answer_publish_gate(client, admin_headers):
    batch = new_batch(client, admin_headers, "2026秋-解析批")
    applicant = register_and_login(client, "stu1001")
    url = f"/api/batches/{batch['id']}/exam-answer"

    # 尚无解析：一律 404（不暴露草稿存在性）
    assert client.get(url, headers=applicant).status_code == 404
    assert client.get(url, headers=admin_headers).status_code == 404
    # 考生无权写入
    assert client.put(url, json={"content": "x", "published": True}, headers=applicant).status_code == 403

    # 管理员存草稿：考生仍 404，管理员可读
    r = client.put(url, json={"content": "一、参考答案A", "published": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["published"] is False
    assert client.get(url, headers=applicant).status_code == 404
    assert client.get(url, headers=admin_headers).json()["content"] == "一、参考答案A"

    # 发布后考生可读，首次发布时间落库
    r = client.put(url, json={"content": "一、参考答案A", "published": True}, headers=admin_headers)
    body = r.json()
    assert body["published"] is True and body["published_at"] is not None
    got = client.get(url, headers=applicant)
    assert got.status_code == 200 and got.json()["content"] == "一、参考答案A"

    # upsert：再保存仍是同一份（batch_id 唯一），内容可更新
    r = client.put(url, json={"content": "v2", "published": True}, headers=admin_headers)
    assert r.json()["content"] == "v2"
