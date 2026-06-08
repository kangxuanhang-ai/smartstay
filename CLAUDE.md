# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# SmartStay (智宿云)

AI 驱动的酒店管理系统。三端客户端，一个 FastAPI 后端。

**重要**：`smartstay-flutter/` 是独立的 Git 仓库（有自己的 `.git` 目录），不在主仓库的版本控制内。

## 技术栈

- **后端**: Python ≥3.11, FastAPI 0.115, SQLModel, asyncpg, LangGraph, pgvector
- **B 端**: React 19, TypeScript 6, Vite 8, Ant Design 6, Zustand, Tailwind CSS 4
- **C 端**: Flutter 3.35+, BLoC, Dio, GoRouter
- **数据库**: PostgreSQL (带 pgvector 扩展)

## 构建与运行

```bash
# 后端 — 需要 PostgreSQL (带 pgvector 扩展) + .env 文件
cd backend && poetry install && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
# B 端 (React 前台/管理前端)
cd frontend && npm install && npm run dev          # → http://localhost:5173

# C 端 (Flutter 住客 App — 先在 smartstay-flutter/lib/core/config.dart 设置后端 IP，写死了的)
cd smartstay-flutter && flutter pub get && flutter run
```

### 必需的 .env 配置项 (backend/.env)

所有配置在 `backend/app/core/config.py` 中有默认值，`.env` 中只需覆盖你要改的。模板文件：`backend/.env.example`、`frontend/.env.example`。

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smartstay
SECRET_KEY=<任意字符串>
DEEPSEEK_API_KEY=<AI 代理用>
SERPAPI_KEY=<联网搜索用，可选>
ALIYUN_ACCESS_KEY_ID=<人脸识别 + 语音识别用>
ALIYUN_ACCESS_KEY_SECRET=<人脸识别 + 语音识别用>
ALIPAY_APP_ID=<支付宝沙箱应用ID>
ALIPAY_PRIVATE_KEY=<应用私钥>
ALIPAY_PUBLIC_KEY=<支付宝公钥>
ALIPAY_RETURN_URL=http://localhost:5173/front-desk/rooms  # 支付成功跳回地址
ALIYUN_FACE_DB_NAME=smartstay_faces                        # 人脸库名称
```

关键默认值：`ACCESS_TOKEN_EXPIRE_MINUTES=15`，`REFRESH_TOKEN_EXPIRE_DAYS=7`，`DEEPSEEK_BASE_URL=https://api.deepseek.com`，`ALIYUN_REGION_ID=cn-shanghai`。

> 注意：`config.py` 中还定义了 `DATABASE_URL_SYNC`（同步连接串）和 `REDIS_URL`，但两者目前均未在代码中使用，无需配置。

### 前端环境变量 (frontend/.env)

```
VITE_API_BASE_URL=http://localhost:8765
VITE_WS_BASE_URL=ws://localhost:8765
```

> 模板文件：`frontend/.env.example`

## 验证命令

完成任务前必须全部运行（按顺序检查：编译 → 类型检查 → 测试）：

```bash
# 后端
cd backend && poetry run python -m py_compile app/main.py   # 类型检查
cd backend && poetry run pytest -x -q                        # 全部测试 (asyncio_mode=auto)
cd backend && poetry run pytest tests/test_auth.py -x -q     # 单个测试文件

# 前端
cd frontend && npx tsc --noEmit                              # 类型检查
cd frontend && npm run lint                                   # lint
cd frontend && npm run build                                  # 生产构建 (tsc -b && vite build)

# Flutter
cd smartstay-flutter && flutter analyze                      # 静态分析
```

环境一键检查：`./init.sh`（验证工具链、.env、数据库连通性、三端编译）。脚本会检查 Python/Node/Flutter 工具链、backend/.env 存在性、PostgreSQL 连通性、TypeScript 类型检查、Flutter 静态分析。

### Docker 生产部署

`docker-compose.yml` 定义了三个服务：`db`（pgvector/pgvector:pg16）、`backend`（FastAPI）、`frontend`（nginx）。模板 `.env.example` 文件在 `backend/` 和 `frontend/` 目录下。

### Git & CI

- **`smartstay-flutter/` 是独立 Git 仓库**，有自己的 `.git` 目录，不在主仓库版本控制内。修改 Flutter 代码时需在该目录内单独 commit/push。
- **CI 流程** (`.github/workflows/deploy.yml`)：push 到 `main` 触发 — Python 3.11 类型检查 + Node 20 前端构建 → SSH 部署到服务器（`docker compose build && up`）。

## ⚠️ 每次任务前必做

当用户要求你**做事**（修 bug、加功能、做改动）时：

1. 读 `session-handoff.md` → 恢复上下文
2. 读 `feature_list.json` → 了解当前进度
3. 创建或更新 feature 条目 → 状态设为 `in-progress`
4. 编码前先读 `docs/superpowers/specs/` 中对应的功能设计文档
5. 编码后：运行验证，更新 `feature_list.json`（状态 + 证据），更新 `progress.md`
6. 用户发下条消息前：更新 `session-handoff.md`

当用户**问问题**（什么是 X、为什么 Y）时，直接回答，无需走清单流程。

## 架构

三端客户端共用一个 FastAPI 后端，入口 `backend/app/main.py`。

### 健康检查

`GET /health` → `{"status": "ok", "version": "1.0.0"}`

### 目录结构

```
backend/app/
  api/          路由处理：auth, rooms, orders, work_orders, admin, consumptions, hotel, ai, rag, face, alipay
  models/       SQLModel 表定义 (16 张表在 __init__.py 导入 + 1 张 guest_preferences = 共 17 张)
  core/         配置 (pydantic-settings)、数据库引擎、认证/安全、依赖注入、种子数据
  ai/           LangGraph 代理：graph, tools, guard, rag, state, pricing, complaint, web_search
  ws/           WebSocket ConnectionManager
  tasks/        APScheduler 定时任务 (每天凌晨 4 点审计报告)
  aliyun/       阿里云 API 客户端 (人脸识别 + 语音识别)

frontend/src/
  pages/        4 个分区：login/, front-desk/, manager/, admin/
  stores/       Zustand authStore (单一 store)
  hooks/        useWebSocket (模块级单例，发布/订阅模式)
  api/          Axios 客户端，带 401 自动刷新拦截器
  components/   共享组件：AppLayout, AuthGuard, ComplaintAlert, ErrorBoundary, FaceCapture

smartstay-flutter/lib/
  blocs/        4 个 BLoC：auth, chat, room, work_order
  pages/        13 个页面，分布在 11 个目录 (含 login/, ai_chat/)
  core/         ApiClient (Dio + JWT 刷新)、WsService、SSE 解析器、config、VoiceService
```

**Flutter 路由结构** (`app.dart`)：
- `/login`, `/face-login`, `/change-password` — 认证相关
- ShellRoute（底部导航栏）：`/home`, `/room-control`, `/ai-chat`, `/work-orders`, `/my`
- 子页面：`/map`, `/facility`（在 /home 下）, `/bill-detail/:orderId`, `/ai-chat/preferences`

### 枚举值（代码中为字符串，非 Python Enum）

- **Room.status**: `vacant`, `occupied`, `dirty`, `maintenance`
- **Room.room_type**: `big_bed`, `twin`, `suite`
- **Order.status**: `pending`, `paid`, `checked_in`, `checked_out`, `completed`
- **Order.source**: `self_app`, `walk_in`, `ota`
- **WorkOrder.type**: `delivery`, `repair`
- **WorkOrder.status**: `submitted`, `accepted`, `processing`, `completed`
- **Staff.role**: `front_desk`, `manager`, `admin`
- **Staff.staff_type**: `housekeeping`, `maintenance`（`None` 表示非蓝领岗位）

### 关键约束

- **价格单位为分 (fen)**：所有金额都是整数。`30000` = 300 元。显示时 ÷ 100。
- **UUID 主键**：所有表使用 `uuid.UUID`，自动生成。
- **双用户模型**：`Guest`（无角色）+ `Staff`（front_desk/manager/admin）。JWT 携带 `user_type` 声明。`get_current_user` 依赖据此从正确的表查询。
- **破坏性迁移**：`init_db()` 每次启动会删除 `rag_embeddings` 和 `users` 表。仅限开发环境，生产环境不安全。`backend/alembic/` 有一次初始迁移，但目前未用于增量迁移——生产环境需手动管理 schema 变更。
- **首次登录强制改密**：所有种子账号初始密码 `123456`，`is_first_login=True`。
- **退房后住客锁定**：退房后 `Guest.is_active=False`，C 端无法登录。再次入住时自动解锁。
- **新员工需入库**：新增的 Staff 模型有 `is_active` 字段。新数据库需手动 `ALTER TABLE staff ADD COLUMN is_active BOOLEAN DEFAULT TRUE`。
- **Staff 的 staff_type 字段**：保洁和维修工的 `role` 都是 `front_desk`，通过 `staff_type`（`housekeeping`/`maintenance`）区分。
- **时间一律用 CST**：`backend/app/core/utils.py` 提供 `cst_now()`（UTC+8 naive datetime）和 `cst_isoformat()`。所有模型的 `created_at` 默认值用 `cst_now`。
- **全局异常处理**：`main.py` 有 catch-all，返回 `{"code": 500, "message": "服务器内部错误", "detail": str(exc)}`。
- **CORS 全开**：`allow_origins=["*"]`，`allow_credentials=False`。
- **登录限流**：`slowapi` 限流，登录接口 `5/minute`（`/api/auth/login` 和 `/api/auth/login/biz`）。

### 数据库模型 (16 张在 __init__.py 导入 + 1 张 guest_preferences = 共 17 张)

```python
# backend/app/models/__init__.py 中导入的模型
Guest, Staff, HotelInfo, Facility, Room, Order, WorkOrder,
Consumption, InvoiceRecord, AIPricingLog, AuditReport,
RAGDocument, RAGEmbedding, AISecurityLog, ChatSession, ChatMessage

# backend/app/models/preference.py 中定义但未在 __init__.py 导入
GuestPreference  # guest_preferences 表
```

> **注意**：`GuestPreference` 模型在 `preference.py` 中定义，但未在 `__init__.py` 中导入。如需使用，需显式导入：`from app.models.preference import GuestPreference`。该表通过 `init_db()` 中的 raw SQL 创建（`CREATE TABLE IF NOT EXISTS guest_preferences`），不通过 SQLModel 自动管理。

### 测试模式

后端测试在 `backend/tests/`，使用 `pytest-asyncio` + `httpx.AsyncClient`：

```python
# backend/tests/conftest.py 提供的 fixtures：
# - client: AsyncClient (ASGITransport)
# - biz_token: 前台登录 token (id_card="qiantai", password="123456")
# - guest_token: 住客登录 token (id_card="100000000000000101", password="123456")

# 写新测试示例 (无需 @pytest.mark.asyncio，asyncio_mode=auto 已配置)：
async def test_something(client, biz_token):
    resp = await client.get(
        "/api/rooms",
        headers={"Authorization": f"Bearer {biz_token}"}
    )
    assert resp.status_code == 200
```

**注意**：`backend/tests/conftest.py` 不会自动 seed 数据。测试依赖数据库中已有种子数据（通过启动服务器或手动 seed）。`biz_token` fixture 会调用 `/api/auth/login/biz`，所以只要服务启动过（触发 lifespan seed），测试就能正常工作。`backend/pytest.ini` 已配置 `asyncio_mode = auto`，测试无需显式加 `@pytest.mark.asyncio`。

### AI 代理 (LangGraph)

`backend/app/ai/graph.py` — StateGraph，5 个节点，条件路由：
- 入口 `route_by_intent`：先检测投诉（`complaint.py`），再走关键词匹配 + LLM 意图分类（4 类：chat/knowledge/action/web_search）
- 节点：`chat_response`（闲聊）、`knowledge_response`（RAG）、`action_response`（工具调用）、`complaint_response`（投诉处理）、`web_search_response`（SerpAPI 联网搜索）
- `action_node`：多步代理循环 (MAX_ITERATIONS=5)，绑定 5 个工具（含 `save_preference_tool`），通过安全守卫执行
- `chat_node`：注入住客姓名、房间号、当前时间、偏好设置、对话摘要
- `knowledge_node`：注入 RAG 结果，含防幻觉指令（"不要编造信息"）
- `web_search_node`：SerpAPI 搜索 → LLM 整理回答。位置相关查询自动拼接酒店地址。开关由前端 `web_search` 参数控制，关闭时降级为闲聊
- 对话摘要：消息 >20 条时自动压缩旧消息为摘要，持久化到 `chat_sessions.summary`

**安全守卫** (`guard.py`)：每个 LLM 工具调用执行前都必须通过守卫。强制执行角色检查、温度范围 (16–30°C)、价格上限 (基础价 150%)、工单限制 (每房间 5 个未完成)。房间 ID 由服务端注入，不信任 LLM 输出。违规写入 `AISecurityLog`。

**RAG** (`rag.py`)：`BAAI/bge-small-zh-v1.5` 嵌入 (512d)，chunk_size=300, overlap=80。LLM query 改写为 2-3 个关键词后分别向量搜索，pgvector 余弦搜索 (top-k=5, 阈值 >0.3)，LIKE 关键词兜底。`POST /api/rag/reindex` 可重建索引。源文档在 `rag_docs/`。

**SSE 流式格式**：AI 聊天返回 `text/event-stream`，JSON 行格式：`{type: "text"|"card"|"done", data: ...}`。

### WebSocket

- **后端** (`app/ws/manager.py`)：`ConnectionManager` — 按用户管理连接，JWT 通过 query 参数认证。方法：`send_to_user`、`broadcast_to_role`、`broadcast_biz`（front_desk+manager+admin）、`send_to_room`（查找已入住住客）。
- **心跳**：后端每 30 秒发 `{"type":"ping"}`，前端 60 秒无消息判定连接已死并强制重连（`main.py` + `useWebSocket.ts`）。
- **前端** (`src/hooks/useWebSocket.ts`)：模块级单例，发布/订阅模式 — 连接一次，按事件类型订阅。工单看板额外有 10 秒轮询兜底（WebSocket 广播可能在断连窗口期丢失）。
- **Flutter** (`lib/core/ws_service.dart`)：单例，最多 5 次重试，指数退避 (3s→30s 上限)。
- 事件：`room.status_change`、`work_order.new`、`work_order.status_change`、`ai_pricing.suggestion`、`payment.success`、`complaint.alert`。

### 支付宝沙箱集成

- **后端** (`app/api/alipay.py`)：创建支付订单、回调处理、支付验证
- **密钥格式**：支付宝 SDK 要求 PKCS#1 格式私钥（`BEGIN RSA PRIVATE KEY`），代码中有 `_ensure_pkcs1_private_key()` 自动转换
- **沙箱网关**：`openapi-sandbox.dl.alipaydev.com`（不是 `openapi.alipaydev.com`）
- **支付验证**：用支付宝 return URL 带回的签名参数验证，不用 `alipay.trade.query`（沙箱 SDK 有 bug）
- **退房结算流程**：点「立即支付」→ 打开支付宝新标签 → 支付成功跳回 → 前端从 return URL 提取参数 → 调后端验签 → 退房

### 其他关键模式

- **401 自动刷新**：Axios (前端) 和 Dio (Flutter) 拦截器均捕获 401，用 refresh token 重试原请求。Flutter 拦截器有 `_retried` 标记防止死循环。
- **双平台 SSE** (Flutter ChatBloc)：Web 用 `fetch` API，原生用 Dio stream — 在 `html_stub.dart` 中处理。
- **500ms 防抖**：设备控制（灯光、窗帘、空调）使用防抖 POST + 乐观更新 UI。
- **阿里云人脸识别**：通过 `backend/app/aliyun/face.py` 实现人脸检测/比对/注册/搜索。人脸库在启动时自动创建。刷脸登录会跳过 `is_active=False` 的住客。人脸比对阈值 75%。
- **阿里云语音识别 (ASR)**：通过 `backend/app/aliyun/asr.py` 实现语音转文字（用于 C 端 AI 聊天语音输入）。使用与人脸识别相同的 `ALIYUN_ACCESS_KEY_ID` 和 `ALIYUN_ACCESS_KEY_SECRET`。
- **房费多日计算**：`total_amount` 始终为单日房价（分），退房后不覆盖。账单通过 `calculate_nights()` 动态计算累计房费。`BillResponse` 包含 `nights` 和 `daily_rate` 字段。大盘今日流水用 `Room.base_price` 计算。
- **工单看板轮询兜底**：`WorkOrderBoard.tsx` 除 WebSocket 监听外，还有 10 秒轮询 + 新工单对比弹框，防止 WebSocket 断连期间广播丢失。

## 种子账号 (密码：`123456`)

**启动时自动 seed 的**（staff + rooms + hotel info + facilities）：

| id_card | 角色 | 姓名 | 备注 |
|---------|------|------|------|
| `qiantai` | front_desk | 前台张 | 测试 fixture 用这个 |
| `dianzhang` | manager | 总店长 | |
| `admin` | admin | 管理员 | |
| `bj001` | front_desk | 王阿姨 | staff_type=housekeeping |
| `bj002` | front_desk | 张阿姨 | staff_type=housekeeping |
| `wx001` | front_desk | 李师傅 | staff_type=maintenance |
| `wx002` | front_desk | 赵师傅 | staff_type=maintenance |

**需要手动调用 `seed_default_guests()` 才会 seed 的**：

| id_card | 姓名 |
|---------|------|
| `100000000000000101` | 住客李 |
| `13042920030603401X` | 康烜航 |

> 注意：`main.py` lifespan 调用 `seed_default_staff()` + `seed_default_rooms()` + `seed_hotel_info()` + `seed_facilities()`，但不调用 `seed_default_guests()`。住客数据需手动 seed 或通过 `seed_default_users()`（同时 seed staff+guests）。启动时还会创建阿里云人脸库。

## 关键文档

- **完整 PRD**：`1. SmartStay-Agent.md`
- **技术设计**：`docs/superpowers/specs/2026-05-23-smartstay-design.md`
- **数据库表结构与关系**：`DATABASE_RELATIONS.md`
- **功能设计文档**：`docs/superpowers/specs/`（每个功能一个）
- **实施计划**：`docs/superpowers/plans/`（每个功能一个）
- **Codex 代理配置**：`AGENTS.md`（旧版本，内容可能落后于本文件）
- **项目深度分析**：`PROJECT_SUMMARY.md`（架构分析报告）
- **UI 设计文件**：`SmartStay.pen`（Pencil 设计文件）

## 工作流规则

1. 一次只做一个功能。开始/完成时更新 `feature_list.json`。
2. 编码前先读对应的功能设计文档。
3. 声称完成前先跑验证。
4. 在 `progress.md` 中记录证据。
5. 会话结束时更新 `session-handoff.md`。

**功能跟踪**：`feature_list.json` 包含所有功能的 ID、名称、状态（planned/in-progress/done）、依赖、设计文档路径、证据。功能 ID 格式为 `F001`、`F002` 等。

**完成标准**：代码编译零错误、全部测试通过、`feature_list.json` 状态为 `done` 且填写了证据、`progress.md` 已更新、`session-handoff.md` 已更新。

**范围**：在范围内 = C 端 Flutter、B 端 React、FastAPI 后端、AI 代理、数据库 schema。除非明确要求，否则不在范围内 = CI/CD、部署、第三方集成、原生应用商店上架、性能优化。
