# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指引。

# SmartStay (智宿云)

AI 驱动的酒店管理系统。三端客户端，一个 FastAPI 后端。

## 构建与运行

```bash
# 后端 — 需要 PostgreSQL (带 pgvector 扩展) + .env 文件
cd backend && poetry install && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# B 端 (React 前台/管理前端)
cd frontend && npm install && npm run dev          # → http://localhost:5173

# C 端 (Flutter 住客 App — 先在 smartstay-flutter/lib/core/config.dart 设置后端 IP，写死了的)
cd smartstay-flutter && flutter pub get && flutter run
```

### 必需的 .env 配置项 (backend/.env)

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/smartstay
SECRET_KEY=<任意字符串>
DEEPSEEK_API_KEY=<AI 代理用>
ALIYUN_ACCESS_KEY_ID=<人脸识别用>
ALIYUN_ACCESS_KEY_SECRET=<人脸识别用>
```

## 验证命令

完成任务前必须全部运行：

```bash
# 后端
cd backend && poetry run python -m py_compile app/main.py   # 类型检查
cd backend && poetry run pytest -x -q                        # 全部测试 (asyncio_mode=auto)
cd backend && poetry run pytest tests/test_auth.py -x -q     # 单个测试文件

# 前端
cd frontend && npx tsc --noEmit                              # 类型检查
cd frontend && npm run lint                                   # lint

# Flutter
cd smartstay-flutter && flutter analyze                      # 静态分析
```

环境一键检查：`./init.sh`（验证工具链、.env、数据库连通性、三端编译）。

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

### 目录结构

```
backend/app/
  api/          路由处理：auth, rooms, orders, work_orders, admin, consumptions, hotel, ai, rag, face
  models/       SQLModel 表定义 (15 张表)
  core/         配置 (pydantic-settings)、数据库引擎、认证/安全、依赖注入、种子数据
  ai/           LangGraph 代理：graph, tools, guard, rag, state, pricing
  ws/           WebSocket ConnectionManager
  tasks/        APScheduler 定时任务 (每天凌晨 4 点审计报告)
  aliyun/       阿里云人脸识别 API 客户端

frontend/src/
  pages/        3 个角色分区：front-desk/, manager/, admin/
  stores/       Zustand authStore (单一 store)
  hooks/        useWebSocket (模块级单例，发布/订阅模式)
  api/          Axios 客户端，带 401 自动刷新拦截器

smartstay-flutter/lib/
  blocs/        4 个 BLoC：auth, chat, room, work_order
  pages/        11 个页面，分布在 10 个目录
  core/         ApiClient (Dio + JWT 刷新)、WsService、SSE 解析器、config
```

### 关键约束

- **价格单位为分 (fen)**：所有金额都是整数。`30000` = 300 元。显示时 ÷ 100。
- **UUID 主键**：所有表使用 `uuid.UUID`，自动生成。
- **双用户模型**：`Guest`（无角色）+ `Staff`（front_desk/manager/admin）。JWT 携带 `user_type` 声明。`get_current_user` 依赖据此从正确的表查询。
- **破坏性迁移**：`init_db()` 每次启动会删除 `rag_embeddings` 和 `users` 表。仅限开发环境，生产环境不安全。
- **首次登录强制改密**：所有种子账号初始密码 `123456`，`is_first_login=True`。

### AI 代理 (LangGraph)

`backend/app/ai/graph.py` — StateGraph，3 个节点，条件路由：
- `process_input` → 意图分类（先走关键词匹配，再走 LLM）
- 路由到：`chat_response`（闲聊）、`knowledge_response`（RAG）、`action_response`（工具调用）
- `action_node`：绑定 4 个工具给 DeepSeek LLM，通过安全守卫执行
- 兜底：如果 LLM 未调用工具，关键词匹配会强制创建工作工单

**安全守卫** (`guard.py`)：每个 LLM 工具调用执行前都必须通过守卫。强制执行角色检查、温度范围 (16–30°C)、价格上限 (基础价 150%)、工单限制 (每房间 5 个未完成)。房间 ID 由服务端注入，不信任 LLM 输出。违规写入 `AISecurityLog`。

**RAG** (`rag.py`)：`BAAI/bge-small-zh-v1.5` 嵌入 (512d)，通过 fastembed，pgvector 余弦搜索 (top-k=5, 阈值 >0.1)。源文档在 `rag_docs/`。

**SSE 流式格式**：AI 聊天返回 `text/event-stream`，JSON 行格式：`{type: "text"|"card"|"done", data: ...}`。

### WebSocket

- **后端** (`app/ws/manager.py`)：`ConnectionManager` — 按用户管理连接，JWT 通过 query 参数认证。方法：`send_to_user`、`broadcast_to_role`、`broadcast_biz`（front_desk+manager+admin）、`send_to_room`（查找已入住住客）。
- **前端** (`src/hooks/useWebSocket.ts`)：模块级单例，发布/订阅模式 — 连接一次，按事件类型订阅。
- **Flutter** (`lib/core/ws_service.dart`)：单例，最多 5 次重试，指数退避 (3s→30s 上限)。
- 事件：`room.status_change`、`work_order.new`、`work_order.status_change`、`ai_pricing.suggestion`。

### 其他关键模式

- **401 自动刷新**：Axios (前端) 和 Dio (Flutter) 拦截器均捕获 401，用 refresh token 重试原请求。
- **双平台 SSE** (Flutter ChatBloc)：Web 用 `fetch` API，原生用 Dio stream — 在 `html_stub.dart` 中处理。
- **500ms 防抖**：设备控制（灯光、窗帘、空调）使用防抖 POST + 乐观更新 UI。
- **阿里云人脸识别**：通过 `backend/app/aliyun/face.py` 实现人脸检测/比对/注册/搜索。人脸库在启动时自动创建。

## 种子账号 (密码：`123456`)

| 身份证号 | 角色 | 用途 |
|---------|------|------|
| `100000000000000001` | front_desk | 前台接待 |
| `100000000000000002` | front_desk + housekeeping | 客房保洁 |
| `100000000000000003` | front_desk + maintenance | 维修工 |
| `100000000000000004` | manager | 经理 |
| `100000000000000005` | admin | 系统管理员 |
| `200000000000000001` | guest | 住客A |
| `200000000000000002` | guest | 住客B |

## 关键文档

- **完整 PRD**：`1. SmartStay-Agent.md`
- **技术设计**：`docs/superpowers/specs/2026-05-23-smartstay-design.md`
- **数据库表结构与关系**：`DATABASE_RELATIONS.md`
- **功能设计文档**：`docs/superpowers/specs/`（每个功能一个）
- **实施计划**：`docs/superpowers/plans/`（每个功能一个）

## 工作流规则

1. 一次只做一个功能。开始/完成时更新 `feature_list.json`。
2. 编码前先读对应的功能设计文档。
3. 声称完成前先跑验证。
4. 在 `progress.md` 中记录证据。
5. 会话结束时更新 `session-handoff.md`。

**完成标准**：代码编译零错误、全部测试通过、`feature_list.json` 状态为 `done` 且填写了证据、`progress.md` 已更新、`session-handoff.md` 已更新。

**范围**：在范围内 = C 端 Flutter、B 端 React、FastAPI 后端、AI 代理、数据库 schema。除非明确要求，否则不在范围内 = CI/CD、部署、第三方集成、原生应用商店上架、性能优化。
