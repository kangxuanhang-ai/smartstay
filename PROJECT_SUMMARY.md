# SmartStay (智宿云) 项目深度分析报告

## 一、项目定位

**AI 驱动的全栈酒店管理系统**，用于 AI 应用开发工程师面试展示。核心链路真实跑通，边缘功能模拟，目标是展示全栈架构能力 + AI 引擎设计 + 安全防御思维。

---

## 二、技术栈

| 端 | 技术选型 |
|---|---------|
| **后端** | Python ≥3.11, FastAPI 0.115, SQLModel, asyncpg, LangGraph, pgvector |
| **B 端 (前台/管理后台)** | React 19, TypeScript 6, Vite 8, Ant Design 6, Zustand, Tailwind CSS 4 |
| **C 端 (住客 App)** | Flutter 3.35+, BLoC, Dio, GoRouter |
| **数据库** | PostgreSQL (带 pgvector 扩展) |
| **AI 引擎** | LangGraph StateGraph + DeepSeek API |
| **实时通信** | WebSocket (FastAPI 原生) |

---

## 三、项目结构

```
my-project/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── core/              # 配置、安全、依赖注入、种子数据
│   │   │   ├── config.py      # 环境变量配置 (pydantic-settings)
│   │   │   ├── security.py    # JWT 签发与校验
│   │   │   ├── deps.py        # 依赖注入 (get_db, get_current_user)
│   │   │   ├── seed.py        # 种子数据
│   │   │   └── utils.py       # 时间工具 (cst_now, cst_isoformat)
│   │   ├── models/            # SQLModel 数据模型 (17 张表)
│   │   │   ├── user.py        # 用户模型 (已拆分)
│   │   │   ├── guest.py       # 住客模型
│   │   │   ├── staff.py       # 员工模型
│   │   │   ├── room.py        # 房间模型
│   │   │   ├── order.py       # 订单模型
│   │   │   ├── work_order.py  # 工单模型
│   │   │   ├── consumption.py # 消费记录
│   │   │   ├── invoice.py     # 发票记录
│   │   │   ├── ai_log.py      # AI 定价日志 + 审计报告
│   │   │   ├── rag.py         # RAG 文档 + 向量嵌入
│   │   │   ├── security_log.py# AI 安全日志
│   │   │   ├── chat.py        # 聊天会话 + 消息
│   │   │   ├── hotel.py       # 酒店信息 + 设施
│   │   │   └── preference.py  # 住客偏好 (GuestPreference)
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── api/               # REST 路由 (12 个模块)
│   │   │   ├── auth.py        # 登录、刷新、改密
│   │   │   ├── rooms.py       # 房间 CRUD + 设备控制
│   │   │   ├── orders.py      # 订单 + 入住 + 退房 + 账单
│   │   │   ├── work_orders.py # 工单管理
│   │   │   ├── consumptions.py# 消费记录
│   │   │   ├── hotel.py       # 酒店信息 + 设施
│   │   │   ├── ai.py          # AI 聊天 + 定价 + 安全日志
│   │   │   ├── rag.py         # RAG 知识库
│   │   │   ├── admin.py       # 管理员沙盒 + 模拟
│   │   │   ├── face.py        # 人脸识别
│   │   │   └── alipay.py      # 支付宝沙箱
│   │   ├── ai/                # AI 引擎 (LangGraph)
│   │   │   ├── graph.py       # StateGraph 定义 (5 节点)
│   │   │   ├── tools.py       # Tool definitions + 意图分类
│   │   │   ├── guard.py       # 安全拦截器
│   │   │   ├── rag.py         # pgvector 知识库操作
│   │   │   ├── state.py       # AgentState 定义
│   │   │   ├── pricing.py     # AI 定价 Agent
│   │   │   ├── complaint.py   # 投诉检测 + 响应
│   │   │   └── web_search.py  # SerpAPI 联网搜索
│   │   ├── ws/                # WebSocket 管理
│   │   │   └── manager.py     # ConnectionManager
│   │   ├── tasks/             # 定时任务
│   │   │   └── audit.py       # 凌晨4点运营审计
│   │   └── aliyun/            # 阿里云 API
│   │       ├── face.py        # 人脸识别
│   │       └── asr.py         # 语音识别
│   └── tests/                 # pytest 测试
├── frontend/                  # React B端 Web 后台
│   ├── src/
│   │   ├── main.tsx           # 入口
│   │   ├── App.tsx            # 路由
│   │   ├── stores/            # Zustand stores (authStore)
│   │   ├── pages/             # 按角色分路由页面
│   │   │   ├── login/         # 登录页
│   │   │   ├── front-desk/    # 前台工作台 (房态格子图、工单看板)
│   │   │   ├── manager/       # 店长大盘 (ECharts)
│   │   │   └── admin/         # 管理沙盒
│   │   ├── components/        # 共享组件
│   │   │   ├── AppLayout.tsx  # 布局
│   │   │   ├── AuthGuard.tsx  # 权限守卫
│   │   │   ├── ComplaintAlert.tsx # 投诉通知
│   │   │   ├── ErrorBoundary.tsx  # 错误边界
│   │   │   └── FaceCapture.tsx    # 人脸拍照
│   │   ├── hooks/             # 自定义 hooks
│   │   │   └── useWebSocket.ts    # WebSocket 单例
│   │   └── api/               # Axios 封装
│   │       └── client.ts      # 401 自动刷新拦截器
├── smartstay-flutter/         # Flutter C端 App (独立 Git 仓库)
│   ├── lib/
│   │   ├── main.dart          # 入口
│   │   ├── app.dart           # GoRouter 路由
│   │   ├── core/              # 核心服务
│   │   │   ├── api_client.dart    # Dio 封装 + JWT 刷新
│   │   │   ├── config.dart        # API base URL (写死 IP)
│   │   │   ├── ws_service.dart    # WebSocket 单例
│   │   │   ├── sse_parser.dart    # SSE 解析
│   │   │   ├── sse_stream_handler.dart # SSE 流处理
│   │   │   └── voice_service.dart # 语音录制
│   │   ├── blocs/             # 4 个 BLoC
│   │   │   ├── auth/          # 认证 (登录、改密、人脸登录)
│   │   │   ├── chat/          # AI 聊天 (双平台 SSE)
│   │   │   ├── room/          # 房间控制 (防抖 IoT)
│   │   │   └── work_order/    # 工单 (WebSocket 刷新)
│   │   ├── pages/             # 13 个页面
│   │   │   ├── home/          # 匿名浏览首页
│   │   │   ├── login/         # 登录 + 人脸登录
│   │   │   ├── change_password/   # 首次改密
│   │   │   ├── room_control/  # 灯光/窗帘/空调
│   │   │   ├── ai_chat/       # AI 管家对话 + 会话历史
│   │   │   ├── work_order/    # 工单时间轴
│   │   │   ├── bill/          # 账单
│   │   │   ├── my/            # 我的页面
│   │   │   ├── facility/      # 设施详情
│   │   │   └── map/           # 地图导航
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 服务层
│   │   └── widgets/           # 共享组件
├── docs/
│   └── superpowers/
│       ├── specs/             # 功能设计文档 (10 个)
│       └── plans/             # 实施计划 (12 个)
├── rag_docs/                  # RAG 知识库源文档
│   ├── 智宿云大酒店服务完全手册.md
│   └── 住客常见问题与详细服务指南.md
├── docker-compose.yml         # Docker 生产部署
├── init.sh                    # 环境一键检查脚本
├── CLAUDE.md                  # Claude Code 配置
├── AGENTS.md                  # Codex 配置
├── progress.md                # 进度日志
├── session-handoff.md         # 会话交接文档
├── feature_list.json          # 功能清单 (17 个功能)
├── DATABASE_RELATIONS.md      # 数据库表关系文档
├── 1. SmartStay-Agent.md      # 完整 PRD
└── 首页.html                  # HTML 原型
```

---

## 四、数据库设计 (17 张表)

### 核心表关系

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   guests    │────<│   orders    │>────│   rooms     │
│  (住客)     │     │   (订单)    │     │   (房间)    │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
  ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
  │staff    │         │work_    │         │chat_    │
  │(员工)   │         │orders   │         │sessions │
  └─────────┘         └─────────┘         └────┬────┘
                                               │
                                          ┌────┴────┐
                                          │chat_    │
                                          │messages │
                                          └─────────┘
```

### 表清单

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| **guests** | 住客 | id_card, phone, name, hashed_password, is_first_login, is_active |
| **staff** | 员工 | id_card, phone, name, hashed_password, role (front_desk/manager/admin), staff_type, is_active |
| **rooms** | 房间 | room_number, room_type, base_price, current_price, status, device_states (JSONB), floor |
| **orders** | 订单 | user_id, room_id, status (pending/paid/checked_in/checked_out/completed), source, total_amount |
| **work_orders** | 工单 | room_id, order_id, type (delivery/repair), content, assigned_resource, status, ai_generated |
| **consumptions** | 消费记录 | order_id, room_id, item_name, category, amount, quantity |
| **invoice_records** | 发票记录 | order_id, company_name, tax_id, email, status |
| **ai_pricing_logs** | AI 定价日志 | room_type, trigger_reason, original_price, suggested_price, status, confirmed_by |
| **audit_reports** | 审计报告 | date, content (JSONB), anomalies (JSONB) |
| **ai_security_logs** | AI 安全日志 | user_id, room_id, role, tool_name, violation_type |
| **rag_documents** | RAG 文档 | title, file_name, content, chunks, uploaded_by |
| **rag_embeddings** | RAG 向量 | document_id, chunk_index, content, embedding (Vector 512d) |
| **chat_sessions** | 聊天会话 | order_id, room_id, status, summary |
| **chat_messages** | 聊天消息 | session_id, role, content, tool_calls (JSONB) |
| **hotel_info** | 酒店信息 | name, address, phone, map_lat, map_lng, description, banner_images |
| **facilities** | 设施 | name, type, open_time, close_time, is_free, price, dynamic_tip |
| **guest_preferences** | 住客偏好 | guest_id, preference_key, preference_value |

### 状态机

**订单状态:** `pending` → `paid` → `checked_in` → `checked_out` → `completed`

**房态:** `vacant` ↔ `occupied` → `dirty` → `vacant` / `maintenance`

**工单:** `submitted` → `accepted` → `processing` → `completed`

---

## 五、API 路由 (12 个模块)

| 模块 | 前缀 | 关键端点 |
|------|------|----------|
| **认证** | `/api/auth` | login (C端), login/biz (B端), refresh, change-password, me |
| **房间** | `/api/rooms` | my-room (C端), my-room/device (控房), / (B端列表), {id}/status |
| **订单** | `/api/orders` | checkin (原子事务), current, {id}/bill, {id}/checkout, {id}/invoice |
| **工单** | `/api/work-orders` | / (创建), my-orders (C端), / (B端列表), {id}/accept, {id}/assign, {id}/complete |
| **消费** | `/api/consumptions` | / (创建), {order_id} (查询) |
| **酒店** | `/api/hotel` | info, facilities, facilities/{id} |
| **AI** | `/api/ai` | chat (SSE), chat/{id}/history, chat/sessions, pricing/logs, safety-threshold, safety-logs, transcribe |
| **RAG** | `/api/rag` | upload, documents, documents/{id}, reindex |
| **管理员** | `/api/admin` | dashboard, audit-report, simulate/*, reset, users |
| **人脸** | `/api/face` | detect, verify, register, search |
| **支付宝** | `/api/alipay` | create, callback, verify |

---

## 六、AI 引擎 (LangGraph)

### StateGraph 结构 (5 节点)

```
route_by_intent
       │
       ├─→ chat_response (闲聊)
       ├─→ knowledge_response (RAG 检索)
       ├─→ action_response (Tool Calling)
       ├─→ complaint_response (投诉处理)
       └─→ web_search_response (SerpAPI 联网)
```

### 意图分类 (4 类)

| 输入示例 | 意图 | 路由目标 |
|---------|------|---------|
| "你好" | `chat` | 直接回复 |
| "泳池几点开" | `knowledge` | RAG → 生成 |
| "房间太热，送双拖鞋" | `action` | Tool Calling |
| "今天天气怎么样" | `web_search` | SerpAPI → 生成 |

### Tools (5 个)

| Tool | 功能 | 权限 |
|------|------|------|
| `control_device_tool` | 控制灯光/窗帘/空调 | guest |
| `create_work_order_tool` | 创建工单 | guest |
| `query_knowledge_tool` | RAG 检索 | guest |
| `modify_room_price_tool` | 改价 | **仅 manager** |
| `save_preference_tool` | 保存偏好 | guest |

### 安全守卫 (Guard)

- 角色校验：非 manager 调改价工具 → 拒绝
- 温度范围：16-30°C
- 价格上限：基础价 150%
- 工单限制：每房间 5 个未完成

### RAG

- 嵌入模型：`BAAI/bge-small-zh-v1.5` (512d)
- 分块：chunk_size=300, overlap=80
- 搜索：pgvector 余弦相似度 (top-k=5, 阈值 >0.3) + LIKE 关键词兜底
- LLM query 改写为 2-3 个关键词

---

## 七、WebSocket 实时通信

### 事件类型

| 事件 | 方向 | 触发时机 |
|------|------|---------|
| `room.status_change` | 后端 → B端 | 房态变更 |
| `work_order.new` | 后端 → B端 | 新工单 |
| `work_order.status_change` | 后端 → C端 | 工单状态变更 |
| `ai_pricing.suggestion` | 后端 → B端 | AI 调价 |
| `payment.success` | 后端 → B端 | 支付成功 |
| `complaint.alert` | 后端 → B端 | 投诉告警 |

### 心跳机制

- 后端每 30 秒发 `{"type":"ping"}`
- 前端 60 秒无消息判定连接已死并强制重连
- Flutter 最多 5 次重试，指数退避 (3s→30s)

---

## 八、关键约束

| 约束 | 说明 |
|------|------|
| **价格单位为分** | 所有金额都是整数，`30000` = 300 元，显示时 ÷ 100 |
| **UUID 主键** | 所有表使用 `uuid.UUID`，自动生成 |
| **双用户模型** | `Guest`（无角色）+ `Staff`（front_desk/manager/admin），JWT 携带 `user_type` |
| **首次登录强制改密** | 所有种子账号初始密码 `123456`，`is_first_login=True` |
| **退房后住客锁定** | 退房后 `Guest.is_active=False`，C 端无法登录，再次入住时自动解锁 |
| **时间一律用 CST** | `cst_now()` (UTC+8 naive datetime)，所有模型 `created_at` 默认值 |
| **CORS 全开** | `allow_origins=["*"]`，`allow_credentials=False` |
| **登录限流** | `slowapi` 限流，登录接口 `5/minute` |

---

## 九、种子账号 (密码：`123456`)

### 启动时自动 seed

| id_card | 角色 | 姓名 | 备注 |
|---------|------|------|------|
| `qiantai` | front_desk | 前台张 | 测试 fixture 用 |
| `dianzhang` | manager | 总店长 | |
| `admin` | admin | 管理员 | |
| `bj001` | front_desk | 王阿姨 | staff_type=housekeeping |
| `bj002` | front_desk | 张阿姨 | staff_type=housekeeping |
| `wx001` | front_desk | 李师傅 | staff_type=maintenance |
| `wx002` | front_desk | 赵师傅 | staff_type=maintenance |

### 需手动 seed

| id_card | 姓名 |
|---------|------|
| `100000000000000101` | 住客李 |
| `13042920030603401X` | 康烜航 |

---

## 十、功能清单 (17 个功能)

| ID | 名称 | 状态 | 依赖 |
|----|------|------|------|
| F001 | Backend core infrastructure | ✅ done | - |
| F002 | B-end React frontend (full) | ✅ done | F001 |
| F003 | C-end Flutter app (initial) | ✅ done | F001 |
| F004 | AI engine (LangGraph + RAG) | ✅ done | F001 |
| F005 | Users table split (guests + staff) | ✅ done | F001 |
| F006 | C-end navigation redesign | 📋 planned | F003 |
| F009 | UTC → 中国标准时间 | ✅ done | - |
| F010 | Bug fixes | ✅ done | F002, F003 |
| F011 | C-end homepage redesign | ✅ done | F003 |
| F012 | C端全页面 UI 重构 | ✅ done | F003, F011 |
| F013 | 人脸识别登录 | ✅ done | F001, F002, F003 |
| F014 | C 端 AI 聊天增强 | ✅ done | F003, F004 |
| F015 | AI Agent 高级优化 | ✅ done | F004 |
| F016 | C 端语音输入 | ✅ done | F003, F004 |
| F018 | C 端 AI 联网搜索 | ✅ done | F004 |

---

## 十一、构建与运行

### 后端

```bash
cd backend && poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

### B 端前端

```bash
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

### C 端 Flutter

```bash
cd smartstay-flutter && flutter pub get && flutter run
# 先在 lib/core/config.dart 设置后端 IP
```

### Docker 生产部署

```bash
docker-compose up -d
# db: pgvector/pgvector:pg16
# backend: FastAPI on :8765
# frontend: nginx on :80/:443
```

### 环境检查

```bash
./init.sh  # 验证工具链、.env、数据库连通性、三端编译
```

---

## 十二、验证命令

### 后端

```bash
cd backend && poetry run python -m py_compile app/main.py   # 类型检查
cd backend && poetry run pytest -x -q                        # 全部测试
```

### 前端

```bash
cd frontend && npx tsc --noEmit                              # 类型检查
cd frontend && npm run build                                 # 生产构建
```

### Flutter

```bash
cd smartstay-flutter && flutter analyze                      # 静态分析
```

---

## 十三、关键文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| **完整 PRD** | `1. SmartStay-Agent.md` | 项目规格说明书 |
| **技术设计** | `docs/superpowers/specs/2026-05-23-smartstay-design.md` | 唯一设计事实来源 |
| **实施计划** | `docs/superpowers/plans/2026-05-23-smartstay-plan.md` | 分阶段 MVP 实施 |
| **数据库关系** | `DATABASE_RELATIONS.md` | 17 张表结构与关系 |
| **Claude 配置** | `CLAUDE.md` | Claude Code 工作指南 |
| **Codex 配置** | `AGENTS.md` | Codex 工作指南 |
| **进度日志** | `progress.md` | 功能完成记录 |
| **会话交接** | `session-handoff.md` | 会话上下文恢复 |
| **功能清单** | `feature_list.json` | 17 个功能状态追踪 |

---

## 十四、项目亮点

1. **全栈架构能力**：三端客户端 (Flutter + React + FastAPI) 共用一套后端，REST + WebSocket 双协议
2. **AI 引擎设计**：LangGraph StateGraph 5 节点条件路由，Tool Calling + RAG + 安全守卫
3. **安全防御思维**：角色校验、参数范围、日志审计三层防御，Prompt 注入攻击拦截
4. **实时通信**：WebSocket 双向推送 + 心跳保活 + 断线重连
5. **支付宝沙箱集成**：完整支付流程 + 签名验证
6. **阿里云集成**：人脸识别 + 语音识别 (ASR)
7. **完善的工程化**：Docker 部署、环境检查脚本、进度追踪文档

---

*报告生成时间：2026-06-05*
