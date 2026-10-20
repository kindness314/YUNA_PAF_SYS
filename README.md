# YUNA_PAF_SYS · 网络信息协会招新系统

面向高校社团招新全流程的一体化系统。设计动机来自真实痛点：去年用飞书多维表格办招新，面试现场乱——打勾式叫号漏叫/错叫、跨部门抢人、重复评分记录、等待时间不可见、现场报名只有名字叫不到人、评分标准五花八门。本系统用**状态机 + 表范式 + 自动调度**从根上消掉这些混乱。

> 需求基线与逐模块实施计划见 **[PLAN.md](./PLAN.md)**（§14 需求基线、§15 实施计划）。

## 核心机制（去年痛点 → 本系统对策）

| 去年的乱 | 本系统机制 |
|---|---|
| 打勾漏叫/忘叫 | 状态机强制流转：候考→已叫号→面试中→完成/过号/缺考，状态只能由动作推进，不可手改 |
| 叫了号人却在别部门面试 | 跨组互斥：进行中的人，其他组叫号自动跳过 |
| 面完没人叫下一位 | **自动调度器**：完成/签到/过号触发同事务补位，缓冲 60s 再叫；可暂停、人工永远可覆盖 |
| 重复评分记录 | `UNIQUE(考生, 面试官)` + upsert，重复提交覆盖而非新增 |
| 等待时间不可见 | 预计等待 = 前方人数 × 平均面时（真实完成时长动态收敛），大屏与签到台可见 |
| 现场报名只有名字 | 发号前强制姓名+手机齐全，缺一当场补录，否则不发号 |
| 导不出未面试名单 | 状态筛选 + 一键 CSV 导出 |
| 分制/评级混用 | 评分三件套统一规范（见下） |

## 评分规范（笔试面试同一套）

- **星级**：0.5 ~ 5 星，半星步进，**必选**
- **分数**：选填，总分按批次自定义（今年 40 分制填 40，不改代码）
- **评价**：必填
- 阅卷人可另写**面试参考批注**（仅面试官可见）；面试官评分页同屏展示该生笔试分/评级/批注

## 两种运行模式

| | 轻量模式（今年） | 全权模式（明年可选） |
|---|---|---|
| 报名 / 笔试收集 | 飞书 → **CSV 导入**（名单+笔试分/评级/批注） | 系统 H5 在线报名与作答 |
| 面试现场（签到/叫号/评分） | **本系统** | 本系统 |
| 录取（综合分排名/发布/查询） | 本系统 | 本系统 |

模块可独立运行，唯一耦合点是 CSV 导入器——资源不够时只跑面试现场+录取也能成场。

## 功能总览

| 功能 | 状态 | 说明 |
|---|---|---|
| 报名 / 临时报名 | 已落地 | 学号每批次唯一（DB 约束）；现场补录打免笔试标记 |
| 笔试题发布 | 已落地（将改 md） | 现为可视化模板；按计划改为版本化 Markdown 文档 |
| 笔试提交 | 已落地 | 窗口期内幂等重复提交，阶段切换自动锁定 |
| 笔试解析公布 | 已落地 | 考后发布题目+参考答案；发布前考生一律 404 |
| 笔试阅卷工作台 | 待做（D3） | 按部门表视图，星级+分数+评价+面试批注 |
| 面试签到 / 发号 | 已落地 | 组内序号原子自增，重复签到唯一约束拒绝 |
| 面试叫号 | 已落地（将升级自动调度） | 条件更新防并发重复叫号；SSE 实时大屏 |
| 面试评分 | 待做（B1） | 星级+分数+评价三件套，面试官可见全部信息 |
| 录取结果查询 | 待做（E） | 综合分 = 笔试×w₁ + 面试×w₂（权重名额可配），本人查询页+发布开关 |
| CSV 导入 | 待做（C） | 飞书导出名单/成绩一键导入，学号 upsert |
| 数据看板 | 已落地 | 漏斗+各部门进度总表，`?fullscreen=1` 投屏 |

实施顺序与验收标准：PLAN.md §15（A 面试现场 → B 评分 → C 导入 → D 笔试链路 → E 录取 → F 演练）。

## 架构

```mermaid
flowchart LR
    subgraph 考生端 H5 [考生端 H5 · Vant]
        A1[报名] --- A2[答卷提交] --- A3[解析/结果查询]
    end
    subgraph 管理端 Admin [管理端 · Element Plus 表范式]
        B1[概览看板] --- B2[报名管理] --- B3[表单/解析编辑]
    end
    subgraph 现场端 [面试现场 · 签到台/叫号台/大屏]
        D1[签到发号] --- D2[自动叫号] --- D3[评分]
    end
    subgraph 服务端 [服务端 FastAPI]
        C1[批次状态机]
        C2[模板/解析 · 版本化]
        C3[队列调度器 · 条件更新]
        C4[统计聚合 · 单一数据源]
        C5[SSE 事件总线]
    end
    DB[(PostgreSQL / 开发用 SQLite)]
    考生端 H5 --> 服务端
    管理端 Admin --> 服务端
    现场端 --> 服务端
    服务端 --> DB
```

单仓三端：`server/`（FastAPI + SQLAlchemy 2.0 + Alembic）、`admin/`（Vue3 + Element Plus + fc-designer + ECharts）、`h5/`（Vue3 + Vant）。

## 快速开始（开发）

前置：Python ≥3.12 + [uv](https://docs.astral.sh/uv/)、Node ≥20。

```bash
# 1. 后端（端口 8100，首次启动自动建表并播种 admin/admin123456）
cd server && uv sync
uv run uvicorn app.main:app --port 8100 --reload
# API 文档：http://localhost:8100/docs

# 2. 管理后台（端口 5173）
cd admin && npm install && npm run dev

# 3. 考生 H5（端口 5174）
cd h5 && npm install && npm run dev
```

前端开发服务器已配置 `/api` 代理至 `127.0.0.1:8100`。

### 演示数据

```bash
cd server
uv run python scripts/seed_demo.py phase1   # 报名期：批次 + 表单 + 6 名报名者
uv run python scripts/seed_demo.py phase2   # 面试日：交卷 ×4 + 签到 ×3 + 叫号 ×1
```

考生演示账号：`20260001 / pass123456`。

### 测试与构建

```bash
cd server && uv run pytest          # 一致性与权限用例（7 项）
cd admin && npm run build
cd h5 && npm run build
```

## 生产部署

```bash
cp .env.example .env                # 必改 YUNA_JWT_SECRET（32+ 字节随机串）
docker compose up -d --build        # postgres + redis + server
```

容器入口自动执行 `alembic upgrade head`；生产置 `YUNA_AUTO_CREATE_DB=false` 走迁移建表。

## 设计要点（详见 PLAN.md）

- **一致性加固**（§12）：约束下沉数据库、写入幂等、SSE 只做刷新信号、派生数据不落列；`server/app/services/queue_service.py` 是条件更新防并发叫号的参考实现。
- **表范式**（§14-9）：管理端/现场端 = 一张主表 + 行内动作；状态列不可手改。
- **批次状态机**：报名→笔试→面试→录取→归档，仅允许逐级推进；单活批次由部分唯一索引保证。

## 维护备忘（踩坑记录）

- `@form-create/vant` 注册的全局组件名是 **`FormCreateMobile`**（`<form-create-mobile>`），与 PC 端 `<form-create>` 不同名。
- Windows 下 `alembic.ini` 必须保持纯 ASCII（configparser 以 locale 编码读取，中文注释在 GBK 环境直接崩溃）；含中文的 Python 文件没问题。
- Windows 本机跑 Alembic 如遇编码问题，命令前加 `PYTHONUTF8=1`。
- 考生约定：**用户名 = 学号**。
- dev.db 若是 `create_all` 建的，先 `alembic stamp <初始版本>` 再 `upgrade head`。

## 目录结构

```
PLAN.md                 计划、需求基线（§14）、模块实施计划（§15）
server/
  app/
    api/routes/         auth / batches / applications / submissions / forms / queue / answers / health
    core/               配置、DB、JWT/bcrypt
    models/             全部领域模型与一致性约束
    services/           队列条件更新、SSE 事件总线、审计日志
  alembic/              迁移
  scripts/seed_demo.py  演示数据
  tests/                API 一致性测试
admin/src/
  views/                登录 / 概览 / 报名管理 / 表单设计(+解析发布) / 面试现场
h5/src/
  views/                登录 / 首页 / 报名 / 笔试答卷 / 笔试解析
```
