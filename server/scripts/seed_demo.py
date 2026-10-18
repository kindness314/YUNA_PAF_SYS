"""演示数据种子。

用法：
    uv run python scripts/seed_demo.py phase1   # 报名期：批次+表单+6名报名者
    uv run python scripts/seed_demo.py phase2   # 面试日：交卷+进面+签到+叫号

依赖运行中的服务 http://127.0.0.1:8100。
"""
import sys

import httpx

BASE = "http://127.0.0.1:8100/api"

APPLY_RULE = {
    "rule": [
        {"type": "input", "field": "intro", "title": "自我介绍",
         "props": {"type": "textarea", "placeholder": "用两三句话介绍自己"}},
        {"type": "input", "field": "work", "title": "作品/主页链接",
         "props": {"placeholder": "如 GitHub / 个人主页，选填"}},
    ]
}

EXAM_RULE = {
    "rule": [
        {"type": "input", "field": "q1", "title": "简述 TCP 三次握手的过程与目的",
         "props": {"type": "textarea", "placeholder": "不限字数"}},
        {"type": "input", "field": "q2", "title": "写一个你参与过的项目，你的角色与贡献",
         "props": {"type": "textarea", "placeholder": "不限字数"}},
    ]
}

APPLICANTS = [
    # 学号, 姓名, 部门, 手机, 现场/线上, 免笔试
    ("20260001", "张一", "技术部", "13800000001", "online", False),
    ("20260002", "李二", "技术部", "13800000002", "online", False),
    ("20260005", "王五", "技术部", "13800000005", "online", False),
    ("20260003", "赵三", "宣传部", "13800000003", "online", False),
    ("20260004", "钱四", "宣传部", "13800000004", "online", False),
    ("20260006", "孙六", "运营部", "13800000006", "onsite", True),
]

ANSWERS = [
    {"q1": "三次握手：SYN → SYN+ACK → ACK，目的是同步双方初始序列号并确认双向链路可达。", "q2": "班级课程表小程序，我负责后端接口与数据库设计。"},
    {"q1": "客户端发 SYN，服务端回 SYN+ACK，客户端再回 ACK；防止历史重复连接并协商序列号。", "q2": "校园二手交易平台，我写前端页面和登录模块。"},
    {"q1": "SYN、SYN+ACK、ACK 三次报文交换，建立可靠传输的起始序号。", "q2": "社团纳新海报设计若干，宣传部推文排版。"},
    {"q1": "握手是建立连接时同步序列号的三次报文交互。", "q2": "运营过社团公众号半年，粉丝增长 800+。"},
]


def client() -> httpx.Client:
    return httpx.Client(base_url=BASE, timeout=10)


def login(c: httpx.Client, username: str, password: str) -> dict:
    r = c.post("/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def active_batch(c: httpx.Client, admin: dict) -> dict:
    r = c.get("/batches", headers=admin)
    r.raise_for_status()
    for b in r.json():
        if b["is_active"]:
            return b
    raise SystemExit("没有进行中的批次，先跑 phase1")


def phase1() -> None:
    c = client()
    admin = login(c, "admin", "admin123456")

    b = c.post("/batches", json={"name": "2026秋季招新（演示）", "year": 2026}, headers=admin)
    b.raise_for_status()
    batch = b.json()

    c.put(f"/forms/{batch['id']}/application", json={"name": "报名表", "schema_json": APPLY_RULE}, headers=admin).raise_for_status()
    c.put(f"/forms/{batch['id']}/exam", json={"name": "笔试卷", "schema_json": EXAM_RULE}, headers=admin).raise_for_status()

    # h5 预览用的考生账号（用户名=学号）
    c.post("/auth/register", json={"username": "20260001", "password": "pass123456", "display_name": "张一"})

    for no, name, dept, phone, source, exempt in APPLICANTS:
        r = c.post("/applications", json={
            "batch_id": batch["id"], "student_no": no, "name": name,
            "phone": phone, "dept_choice": dept, "source": source,
            "exempt_exam": exempt,
            "extra": {"intro": f"我是{name}，希望加入{dept}。", "work": ""},
        }, headers=admin)
        r.raise_for_status()
    print(f"phase1 ok: batch={batch['name']} stage=registration, applied={len(APPLICANTS)}")


def phase2() -> None:
    c = client()
    admin = login(c, "admin", "admin123456")
    batch = active_batch(c, admin)

    c.patch(f"/batches/{batch['id']}/stage", json={"stage": "exam"}, headers=admin).raise_for_status()
    template = c.get(f"/forms/{batch['id']}/exam", headers=admin).json()

    apps = c.get("/applications", params={"batch_id": batch["id"], "size": 100}, headers=admin).json()
    submittable = [a for a in apps if not a["exempt_exam"]]
    for a, ans in zip(submittable, ANSWERS):
        c.post("/submissions", json={"application_id": a["id"], "template_id": template["id"], "data": ans}, headers=admin).raise_for_status()

    c.patch(f"/batches/{batch['id']}/stage", json={"stage": "interview"}, headers=admin).raise_for_status()
    group = c.post("/queue/groups", json={"batch_id": batch["id"], "name": "技术组A"}, headers=admin).json()

    tech = [a for a in apps if a["dept_choice"] == "技术部"]
    for a in tech[:3]:
        c.post("/queue/checkin", json={"group_id": group["id"], "application_id": a["id"]}, headers=admin).raise_for_status()
    called = c.post(f"/queue/groups/{group['id']}/call", json={"room": "1号面试间"}, headers=admin)
    called.raise_for_status()
    print(f"phase2 ok: stage=interview, submitted={len(ANSWERS)}, group={group['name']}, "
          f"checked_in={min(3, len(tech))}, first_call_seq={called.json().get('seq')}")


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "phase1"
    {"phase1": phase1, "phase2": phase2}[phase]()
