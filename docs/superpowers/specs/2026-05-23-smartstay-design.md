# SmartStay（智宿云）全栈酒店系统 — 设计规格说明书

> 本文件为项目完整设计文档，覆盖：技术选型、数据模型、API 路由、AI 引擎、前后端架构。
> 原始需求来自 `docs/smartstay/1. SmartStay-Agent.md`

---

## 1. 项目概述

### 1.1 定位

AI 应用开发工程师面试展示项目。核心链路真实跑通，边缘功能模拟。目标是向面试官展示全栈架构能力 + AI 引擎设计 + 安全防御思维。

### 1.2 系统架构

| 层 | 技术选型 |
|---|---------|
| C端 App | Flutter + Bloc + GoRouter |
| B端 Web | React 18 + Vite + Ant Design 5 + ECharts + Zustand + Tailwind CSS |
| 后端 | FastAPI + SQLModel + Poetry |
| AI 引擎 | LangGraph (完整 State Graph) + DeepSeek-v4-flash 官方 API |
| 数据存储 | PostgreSQL + pgvector |
| 实时通信 | WebSocket (FastAPI 原生) |
| 开发环境 | Docker (PostgreSQL + pgvector + Redis 已运行) + 本地热重载 (后端/前端) |
| 测试 | pytest 覆盖核心链路 |
| 代码组织 | 主仓 (FastAPI + React) + Flutter 独立仓 |

### 1.3 代码组织

**主仓目录结构：**

```
smartstay/
├── docker/                    # Docker Compose (PostgreSQL + pgvector)
│   └── docker-compose.yml
├── backend/                   # FastAPI 后端
│   ├── pyproject.toml         # Poetry 依赖管理
│   ├── alembic/               # 数据库迁移
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── core/              # 配置、安全、依赖注入
│   │   │   ├── config.py      # 环境变量配置
│   │   │   ├── security.py    # JWT 签发与校验
│   │   │   └── deps.py        # 依赖注入 (get_db, get_current_user)
│   │   ├── models/            # SQLModel 数据模型
│   │   │   ├── user.py
│   │   │   ├── room.py
│   │   │   ├── order.py
│   │   │   └── work_order.py
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── api/               # REST 路由
│   │   │   ├── auth.py        # 登录、注册、密码修改
│   │   │   ├── rooms.py       # 房间 CRUD
│   │   │   ├── orders.py      # 订单管理
│   │   │   └── work_orders.py # 工单管理
│   │   ├── ws/                # WebSocket 管理
│   │   │   └── manager.py     # ConnectionManager
│   │   ├── ai/                # AI 引擎
│   │   │   ├── graph.py       # LangGraph State Graph 定义
│   │   │   ├── tools.py       # Tool definitions (RAG, Business API)
│   │   │   ├── guard.py       # 安全拦截器
│   │   │   └── rag.py         # pgvector 知识库操作
│   │   └── tasks/             # 定时任务
│   │       └── audit.py       # 凌晨4点运营审计
│   └── tests/
│       ├── test_auth.py
│       ├── test_orders.py
│       ├── test_work_orders.py
│       └── test_ai_tools.py
├── frontend/                  # React B端 Web 后台
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── stores/            # Zustand stores (auth, rooms, workOrders)
│   │   ├── pages/             # 按角色分路由页面
│   │   │   ├── login/
│   │   │   ├── front-desk/    # 前台工作台
│   │   │   ├── manager/       # 店长大盘
│   │   │   └── admin/         # 管理沙盒
│   │   ├── components/        # 共享组件
│   │   ├── hooks/             # 自定义 hooks (WebSocket 等)
│   │   └── api/               # Axios 封装 + OpenAPI 生成类型
│   └── ...
└── scripts/                   # 启动脚本、Mock 数据生成
```

---

## 2. 数据库设计

### 2.1 users（用户表）— 所有角色共用

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 自增主键 |
| id_card | VARCHAR(18) | UNIQUE, NOT NULL | 身份证号，唯一索引 |
| phone | VARCHAR(11) | NOT NULL | 手机号 |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt 加密密码，默认 123456 |
| is_first_login | BOOLEAN | DEFAULT TRUE | 首次登录强制改密 |
| role | VARCHAR(20) | DEFAULT 'guest' | guest / front_desk / manager / admin |
| created_at | TIMESTAMP | DEFAULT NOW() | — |

**角色登录隔离：**
- C端登录接口：`WHERE role = 'guest'`
- B端登录接口：`WHERE role IN ('front_desk', 'manager', 'admin')`

### 2.2 hotel_info（酒店信息表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| name | VARCHAR(100) | 酒店名称 |
| address | VARCHAR(200) | 地址 |
| phone | VARCHAR(20) | 虚拟前台电话 |
| map_lat | FLOAT | Mock 纬度 |
| map_lng | FLOAT | Mock 经度 |
| description | TEXT | 图文长介绍 |
| banner_images | JSONB | `["url1","url2","url3"]` 轮播图 |

### 2.3 facilities（配套设施表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| name | VARCHAR(50) | 如 "无边泳池" |
| type | VARCHAR(20) | gym / pool / restaurant / laundry |
| open_time | TIME | 营业时间 |
| close_time | TIME | 关门时间 |
| is_free | BOOLEAN | 是否免费 |
| price | INTEGER (nullable) | 收费价格（分） |
| dynamic_tip | JSONB | `{"water_temp":"26°C","crowd_level":"空闲"}` |

### 2.4 rooms（房间表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID PK | — | — |
| room_number | VARCHAR(10) | UNIQUE, NOT NULL | 如 "301" |
| room_type | VARCHAR(20) | NOT NULL | big_bed / twin / suite |
| base_price | INTEGER | NOT NULL | 基础价（分） |
| current_price | INTEGER | NOT NULL | 当前价，AI 可调 |
| status | VARCHAR(20) | NOT NULL | vacant / occupied / dirty / maintenance |
| device_states | JSONB | DEFAULT '{}' | `{"living_light":false,"bedroom_light":true,"curtain":50,"ac_temp":24,"ac_mode":"cool"}` |
| floor | INTEGER | — | 楼层 |

**房态状态机：**
```
VACANT ←(保洁完成)── DIRTY ←(退房)── OCCUPIED
  │                        ▲
  └──(报修)──▶ MAINTENANCE ──(修复)──┘
```

### 2.5 orders（订单表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID PK | — | — |
| user_id | UUID | FK → users | 关联用户 |
| room_id | UUID | FK → rooms | 关联房间 |
| status | VARCHAR(20) | NOT NULL | pending / paid / checked_in / checked_out / completed |
| check_in_time | TIMESTAMP | — | 实际入住时间 |
| check_out_time | TIMESTAMP | — | 实际退房时间 |
| total_amount | INTEGER | NOT NULL | 总金额（分） |
| source | VARCHAR(20) | NOT NULL, DEFAULT 'self_app' | 订单来源：self_app / ctrip / meituan |
| created_at | TIMESTAMP | DEFAULT NOW() | — |

**订单状态机：**
```
PENDING ──(支付)──▶ PAID ──(入住)──▶ CHECKED_IN ──(退房)──▶ CHECKED_OUT ──(归档)──▶ COMPLETED
```

**前台开房（关键原子事务）：**
1. 检查身份证 → users 表是否存在？不存在则 INSERT（初始密码 123456）
2. INSERT order (user_id, room_id, status=CHECKED_IN)
3. UPDATE rooms SET status='OCCUPIED'
4. 任何一步失败 → ROLLBACK 全部回滚

### 2.6 work_orders（工单表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID PK | — | — |
| room_id | UUID | FK → rooms | 关联房间 |
| order_id | UUID | FK → orders, nullable | 关联订单 |
| type | VARCHAR(20) | NOT NULL | delivery / repair |
| content | TEXT | NOT NULL | 需求描述 |
| assigned_resource | VARCHAR(50) | — | 指派人员姓名 |
| status | VARCHAR(20) | NOT NULL | submitted / accepted / processing / completed |
| ai_generated | BOOLEAN | DEFAULT FALSE | 是否由 AI 拆解创建 |
| created_at | TIMESTAMP | DEFAULT NOW() | — |
| updated_at | TIMESTAMP | — | 最后变更时间 |

**工单状态机：**
```
SUBMITTED ──(前台接单)──▶ ACCEPTED ──(指派处理)──▶ PROCESSING ──(确认完成)──▶ COMPLETED
```

### 2.7 consumptions（消费记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| order_id | FK → orders | 关联订单 |
| room_id | FK → rooms | 关联房间 |
| item_name | VARCHAR(100) | "客房小冰箱·可乐" / "中餐厅·红烧肉套餐" |
| category | VARCHAR(20) | minibar / restaurant / laundry / other |
| amount | INTEGER | 金额（分） |
| quantity | INTEGER | 数量 |
| consumed_at | TIMESTAMP | 消费时间 |
| created_by | VARCHAR(20) | guest / ai / front_desk |

### 2.8 invoice_records（发票登记表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| order_id | FK → orders | 关联订单 |
| company_name | VARCHAR(100) | 公司抬头 |
| tax_id | VARCHAR(30) | 企业税号 |
| email | VARCHAR(100) | 接收邮箱 |
| status | VARCHAR(20) | draft / submitted / issued |
| created_at | TIMESTAMP | DEFAULT NOW() |

### 2.9 ai_pricing_logs（AI 调价日志表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| room_type | VARCHAR(20) | 影响的房型 |
| trigger_reason | TEXT | "周边体育馆突发人流涌入" |
| original_price | INTEGER | 原价 |
| suggested_price | INTEGER | 建议价 |
| status | VARCHAR(20) | pending / approved / rejected |
| suggested_by | VARCHAR(50) | "AI · 定价Agent" |
| confirmed_by | FK → users (nullable) | Manager 审批人 |
| created_at | TIMESTAMP | — |
| decided_at | TIMESTAMP (nullable) | 审批时间 |

**硬安全死规则：** 涨幅不超过 base_price 的 50%，且必须人工确认。

### 2.10 audit_reports（AI 审计报告表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| date | DATE | 审计日期 |
| content | JSONB | 结构化报告内容 |
| anomalies | JSONB | `[{"room":"302","issue":"连续催促>3次"},{"staff":"张阿姨","overtime_count":5}]` |
| generated_at | TIMESTAMP | 生成时间 |

### 2.11 ai_security_logs（AI 安全拦截日志表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| user_id | FK → users | 触发拦截的用户 |
| room_id | FK → rooms (nullable) | 来源房间 |
| role | VARCHAR(20) | 用户角色 |
| tool_name | VARCHAR(100) | 被拦截的 Tool 名称 |
| tool_params | JSONB | LLM 尝试传入的参数 |
| violation_type | VARCHAR(50) | ROLE_VIOLATION / PRICE_LIMIT / PARAM_ABUSE |
| user_input | TEXT | 原始用户输入（疑似注入语句） |
| intercepted_at | TIMESTAMP | 拦截时间 |

### 2.12 RAG 相关表

**rag_documents（知识库文档表）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| title | VARCHAR(200) | 文档标题 |
| file_name | VARCHAR(200) | 原始文件名 |
| content | TEXT | 原始 Markdown |
| chunks | INTEGER | 切片数量 |
| uploaded_by | FK → users | 上传人 |
| uploaded_at | TIMESTAMP | — |
| vectorized_at | TIMESTAMP (nullable) | 向量化完成时间 |

**rag_embeddings（pgvector 向量表）：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| document_id | FK → rag_documents | 关联文档 |
| chunk_index | INTEGER | 切片序号 |
| content | TEXT | 切片文本 |
| embedding | vector(1536) | DeepSeek Embedding |

### 2.13 聊天记录表

**chat_sessions：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| order_id | FK → orders | 关联订单 |
| room_id | FK → rooms | 关联房间 |
| status | VARCHAR(20) | active / closed |
| created_at | TIMESTAMP | — |

**chat_messages：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | — |
| session_id | FK → chat_sessions | 关联会话 |
| role | VARCHAR(20) | user / assistant / tool |
| content | TEXT | 消息内容 |
| tool_calls | JSONB (nullable) | Tool 调用记录 |
| created_at | TIMESTAMP | — |

---

## 3. API 路由设计

### 3.1 认证模块 `/api/auth`

| 方法 | 路由 | 说明 | 涉及表 |
|------|------|------|--------|
| POST | `/api/auth/login` | C端登录（role=guest）→ 双 Token | `users` |
| POST | `/api/auth/login/biz` | B端登录（role IN front_desk,manager,admin）→ 双 Token + role | `users` |
| POST | `/api/auth/refresh` | refresh_token 换新 access_token | — |
| POST | `/api/auth/change-password` | 首次登录强制改密，is_first_login → FALSE | `users` |

### 3.2 酒店信息模块 `/api/hotel`（C端匿名可访问）

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/hotel/info` | 酒店基本信息 + banner 轮播图 |
| GET | `/api/hotel/facilities` | 配套设施列表 |
| GET | `/api/hotel/facilities/{id}` | 设施详情 + 动态提示 |

### 3.3 房间与设备控制 `/api/rooms`

| 方法 | 路由 | 说明 | 涉及表 |
|------|------|------|--------|
| GET | `/api/rooms/my-room` | C端：查当前住客房间信息 + 设备状态 | `rooms`, `orders` |
| POST | `/api/rooms/my-room/device` | C端：控制灯光/窗帘/空调（body: `{device, state}`） | `rooms` |
| GET | `/api/rooms` | B端：全部房间列表（房态格子图） | `rooms` |
| PUT | `/api/rooms/{id}/status` | B端：改房态（脏房/锁房/维修） | `rooms` |

### 3.4 订单模块 `/api/orders`

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/orders/checkin` | 前台开房（原子事务：user + order + room） |
| GET | `/api/orders/current` | C端：查当前住客的活跃订单 |
| GET | `/api/orders/{id}/bill` | C端：查挂房账明细（房费 + consumptions） |
| PUT | `/api/orders/{id}/checkout` | 退房：订单 → CHECKED_OUT，房态 → DIRTY |
| PUT | `/api/orders/{id}/invoice` | 发票预登记 |

### 3.5 工单模块 `/api/work-orders`

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/work-orders` | 创建工单（AI Tool 调用或 C端手动） |
| GET | `/api/work-orders/my-orders` | C端：查当前房间所有工单（时间轴） |
| GET | `/api/work-orders` | B端：查所有待处理工单（看板） |
| PUT | `/api/work-orders/{id}/accept` | 接单：SUBMITTED → ACCEPTED |
| PUT | `/api/work-orders/{id}/assign` | 指派：写入 assigned_resource → PROCESSING |
| PUT | `/api/work-orders/{id}/complete` | 核销：PROCESSING → COMPLETED |

### 3.6 消费记录 `/api/consumptions`

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/consumptions` | 录入消费 |
| GET | `/api/consumptions/{order_id}` | 查某订单的全部消费 |

### 3.7 AI 引擎 `/api/ai`

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/ai/chat` | AI 管家对话入口（SSE 流式返回） |
| GET | `/api/ai/chat/{session_id}/history` | 查历史对话 |
| GET | `/api/ai/pricing/logs` | B端：查看 AI 调价历史 |
| PUT | `/api/ai/pricing/{log_id}/approve` | 批准调价 |
| PUT | `/api/ai/pricing/{log_id}/reject` | 拒绝调价 |
| POST | `/api/ai/safety-threshold` | 店长设置安全阈值 |
| GET | `/api/ai/safety-logs` | 管理员查看安全拦截日志 |

### 3.8 RAG 知识库 `/api/rag`（B端店长）

| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/rag/upload` | 上传 Markdown → 切片 → 向量化 |
| GET | `/api/rag/documents` | 文档列表 |
| DELETE | `/api/rag/documents/{id}` | 删除知识库文档 |

### 3.9 审计与管理 `/api/admin`（店长 + 管理员）

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/admin/dashboard` | 入住率/RevPAR/流水/渠道数据 |
| GET | `/api/admin/audit-report` | 最新运营审计报告 |
| POST | `/api/admin/simulate/door-open` | 模拟门锁打开（管理员） |
| POST | `/api/admin/simulate/event` | 模拟外部舆情事件（管理员） |
| POST | `/api/admin/simulate/prompt-inject` | 模拟 Prompt 注入（管理员） |
| POST | `/api/admin/reset` | 数据重置 |
| POST | `/api/admin/users` | 创建 B端员工账号 |

---

## 4. WebSocket 消息协议

| 事件名 | 方向 | 触发时机 | 消息体 |
|--------|------|---------|--------|
| `work_order.new` | 后端 → B端 | C端 AI 创建新工单 | `{order_id, room_number, type, content}` |
| `work_order.status_change` | 后端 → C端 | B端接单/指派/核销 | `{order_id, new_status, message}` |
| `ai_pricing.suggestion` | 后端 → B端 | AI 触发调价 | `{log_id, room_type, original, suggested, reason}` |
| `room.status_change` | 后端 → B端 | 房态变更 | `{room_id, old_status, new_status}` |

**连接管理：**
- 校验 JWT，建立 `{user_id → websocket}` 映射
- C端按 `order_id` → `room_id` 订阅，只接收本房间推送
- B端按 `role` 订阅不同范围

---

## 5. AI 引擎设计

### 5.1 LangGraph State Graph 结构

```
process_input → summarize → classify
                                │
               ┌────────────────┼────────────────┐
               ▼                ▼                ▼
          [直接回复]      [RAG 检索]     [Tool Calling]
               │                │                │
               │                ▼                │
               │           [生成回答]             │
               │                │                │
               ▼                ▼                ▼
                       format_output
```

### 5.2 意图路由（classify 节点）

| 输入示例 | 意图 | 路由目标 |
|---------|------|---------|
| "你好，今天天气怎么样" | `chat` | 直接回复 |
| "无边泳池几点开门" | `knowledge` | RAG 检索 → 生成 |
| "房间太热，顺便送两双拖鞋" | `action` | Tool Calling（控温 + 创建工单） |
| "帮我把大床房价格改成1元" | `action` | Tool Calling → Guard 拒绝 |
| "马桶堵了，快找人来修" | `action` | Tool Calling（创建工单） |

### 5.3 Tool Calling 定义

| Tool | 功能 | 权限 |
|------|------|------|
| `control_device_tool` | 控制灯光/窗帘/空调 | guest |
| `create_work_order_tool` | 创建送物/报修工单 | guest |
| `query_knowledge_tool` | 检索 RAG 知识库 | guest |
| `modify_room_price_tool` | 修改房间价格 | **仅 manager** |

### 5.4 安全拦截器（Guard）

```
Tool 调用前 → 检查 user.role
  ├─ modify_room_price_tool → 非 manager → "权限不足，拒绝执行" → 日志写入 ai_security_logs
  ├─ control_device_tool → 温度边界（16-30°C）
  └─ create_work_order_tool → 单次上限 5 个工单
```

### 5.5 RAG 流程

```
上传 Markdown → TextSplitter(chunk_size=500, overlap=50) → DeepSeek Embedding(1536维) → pgvector
查询 → Embedding → pgvector 余弦相似度 Top-5 → 拼入 System Prompt → LLM 生成
```

### 5.6 AI 定价 Agent

```
舆情/外部数据 → 定价 Agent 计算 → INSERT ai_pricing_logs(pending)
→ WebSocket 弹窗 B端 → Manager 确认/拒绝 → 写入 rooms.current_price
硬约束：涨幅 ≤ base_price × 50%
```

### 5.7 AI 审计 Agent（凌晨 4:00）

```
采集 24h 内：工单耗时 + 客诉文本 + 连续催促 >3次的房间
→ LLM Reflection 反思模式 → 生成结构化报告
→ INSERT audit_reports → 店长次日首页查看
```

### 5.8 SSE 流式输出格式

```
{ "type": "text", "content": "正在为您将空调调低至22°C..." }
{ "type": "card", "card": { "type": "device", "icon": "ac", "title": "空调调节中", "status": "processing" } }
{ "type": "card", "card": { "type": "delivery", "icon": "package", "title": "物品配送工单已创建", "status": "submitted" } }
{ "type": "done" }
```

---

## 6. B端业务逻辑

### 6.1 前台接待工作台（Front Desk）

| 操作 | 逻辑 | 涉及表 |
|------|------|--------|
| 实时房态格子图 | 查全部 rooms，按 status 着色（绿/红/黄/灰） | `rooms` |
| 快捷开房（右键菜单） | 点击空房 → 标注已占 | `rooms` |
| 设为脏房 | 手动标注需要保洁 | `rooms` |
| 一键锁房/解锁 | 锁定房间不可入住 | `rooms` |
| 线下入住登记 | 原子事务：创建用户 + 创建订单 + 改房态 OCCUPIED | `users`, `orders`, `rooms` |
| 退房 | 订单 → CHECKED_OUT，房态 → DIRTY | `orders`, `rooms` |
| 工单看板（WebSocket） | 左列待指派 / 右列处理中/已完成 → 新工单弹窗+提示音 | `work_orders` |
| 接单 | SUBMITTED → ACCEPTED → WS推送C端 | `work_orders` |
| 指派保洁/维修 | 下拉选人 → assigned_resource 写入 → PROCESSING | `work_orders` |
| 核销完成 | PROCESSING → COMPLETED → WS推送C端「已送达」 | `work_orders` |
| AI 调价弹窗 | 阻断式弹窗 → 批准/拒绝 → 写入 rooms.current_price | `ai_pricing_logs`, `rooms` |
| 查看工单历史 | 按房间/日期筛选 | `work_orders` |

### 6.2 总店长决策大盘（Manager）

| 操作 | 逻辑 | 涉及表 |
|------|------|--------|
| AI 审计报告 | 查看凌晨4:00生成的运营异常报告 | `audit_reports` |
| 入住率图表 | ECharts：OCCUPIED ÷ 总房间数 | `rooms` |
| RevPAR 图表 | 当日总流水 ÷ 可售房间数 | `orders`, `rooms` |
| 全天总流水走势 | 按小时聚合 | `orders`, `consumptions` |
| 渠道对比图 | 按 source 字段 GROUP BY（self_app/ctrip/meituan） | `orders` |
| 安全阈值设置 | 输入最大溢价百分比 | ai_pricing_logs 硬逻辑 |
| 知识库文档上传 | Markdown → 切片 → 向量化 | `rag_documents`, `rag_embeddings` |
| AI 调价历史 | 所有定价建议审批记录 | `ai_pricing_logs` |
| 消费明细查询 | 按房间/时间段查询 | `consumptions` |
| 发票记录管理 | 查看/导出/标记 | `invoice_records` |
| 用户管理 | 创建/禁用 B端员工账号 | `users` |

### 6.3 系统管理员沙盒（Admin）

| 操作 | 逻辑 | 涉及表 |
|------|------|--------|
| 模拟门锁打开 | Webhook → 订单推进 CHECKED_IN | `orders`, `rooms` |
| 模拟外部舆情 | 注入上下文 → 观察 AI 定价 Agent | `ai_pricing_logs` |
| 模拟 Prompt 注入 | 注入恶意文本 → 查看 Guard 拦截 | `ai_security_logs` |
| 安全防御日志 | 展示所有被拦截记录 | `ai_security_logs` |
| 数据重置 | 恢复演示数据库初始状态 | 全部表 |
| Mock 数据注入 | 批量生成虚拟数据 | `users`, `orders`, `consumptions`, `work_orders` |

---

## 7. C端业务逻辑

### 7.1 匿名浏览（无需登录）

| 功能 | 说明 | 涉及表 |
|------|------|--------|
| 酒店首页橱窗 | Banner 轮播图 + 图文介绍 | `hotel_info` |
| 一键导航 | 调用手机地图 APP，用 Mock 经纬度规划路线 | `hotel_info` |
| 一键拨号 | 调用原生电话拨打虚拟号码 | `hotel_info` |
| 配套设施浏览 | 网格展示：健身房/泳池/餐厅/洗衣房 + 详情页 | `facilities` |

### 7.2 Auth Gate 登录验证

| 功能 | 说明 |
|------|------|
| 路由守卫拦截 | 未登录点击功能入口 → 强制跳转登录页 + 缓存目标路由 |
| 用户登录 | 身份证号 + 初始密码 123456 → JWT 双 Token → 本地持久化 |
| Token 无感刷新 | access_token 过期 → refresh_token 自动换新 |
| 首次登录强制改密 | is_first_login=TRUE → 路由锁死改密页 → 提交后进入主页 |

### 7.3 已入住 · 数字化客房工作台

**智能家居控制面板：**

| 功能 | 说明 | 涉及表 |
|------|------|--------|
| 灯光控制 | 三组开关（客厅/卧室/床头），点击切换 + UI 亮灭动画 | `rooms` (device_states) |
| 窗帘控制 | Slider 滑动条 0%-100% 开合 | `rooms` |
| 空调控制 | Dial 刻度盘 16°C-30°C，制冷/制热切换 | `rooms` |

**C端约束：** 所有控房组件挂载 500ms 防抖机制。

**AI 虚拟管家对话：**

| 功能 | 说明 |
|------|------|
| 流式对话 | Token-by-Token SSE 流式输出 |
| 意图拆解 + 业务卡片 | 「房间太热，送双拖鞋」→ 拆成 2 个意图 → 流式回复 + 业务卡片 |
| 知识库问答 | 查询 RAG 知识库 → LLM 组织回答 |
| 业务创建 | 自然语言 → Tool Calling → 创建工单/控制设备 |

**服务追踪与账单：**

| 功能 | 说明 |
|------|------|
| 工单时间轴 | 本房间全部工单进度：已提交→接单→处理中→已送达（WebSocket 实时刷新） |
| 实时挂房账 | 房费 + 消费明细 + 押金剩余比例 |
| 发票预登记 | 公司抬头、税号、邮箱 → 同步 B端 |

---

## 8. 安全模型

### 8.1 JWT 双 Token 机制

- **access_token**: 有效期 15 分钟，携带 user_id + role，用于 API 鉴权
- **refresh_token**: 有效期 7 天，仅用于换发 access_token
- **刷新流程**: 网络拦截器检测 401 → 自动调用 `/api/auth/refresh` → 重试原请求，用户无感知

### 8.2 RBAC 权限矩阵

| 角色 | C端 API | B端 API（前台） | B端 API（店长） | B端 API（管理员） |
|------|---------|---------------|---------------|-----------------|
| guest | ✅ 全部 | ❌ | ❌ | ❌ |
| front_desk | ❌ | ✅ 全部 | ❌ | ❌ |
| manager | ❌ | ❌ | ✅ 全部 | ❌ |
| admin | ❌ | ❌ | ❌ | ✅ 全部 |

### 8.3 AI 安全纵深防御

1. **角色校验（Guard 层）**: Tool 执行前校验 user.role，非 manager 调用 modify_room_price_tool 直接拒绝
2. **参数范围校验**: 温度 16-30°C，价格涨幅 ≤ 50%，单次工单 ≤ 5
3. **日志审计**: 所有拦截事件写入 ai_security_logs，管理员沙盒可回溯

### 8.4 统一错误码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 400 | 参数校验失败 |
| 401 | Token 过期或无效 |
| 403 | 角色权限不足 |
| 404 | 资源不存在 |
| 409 | 业务冲突（如已入住不可重复开房） |
| 422 | 数据验证失败（Pydantic） |
| 500 | 服务端异常 |

---

## 9. Mock 数据策略

### 9.1 Seed 数据（首次启动注入）

- 1 条 hotel_info（酒店基础信息）
- 4-6 条 facilities（配套设施）
- 10-15 条 rooms（不同楼层、类型、初始状态）
- 3 个 B端员工账号（front_desk, manager, admin 各 1）
- 2-3 个 C端住客账号

### 9.2 演示数据（管理员沙盒一键注入）

- 20 条消费记录
- 10 条已完成工单
- 5 条已完成订单
- 1 条 AI 审计报告

### 9.3 数据重置

POST `/api/admin/reset` → truncate 所有业务表 → 重新执行 seed。

---

## 10. 错误处理规范

- 所有 API 返回统一格式: `{"code": int, "message": str, "data": optional}`
- 后端异常中间件统一捕获未处理异常，返回 500
- SQLModel 异步事务：`async with session.begin()`，任何异常自动 ROLLBACK
- AI 对话异常：Tool 调用失败时 LLM 友好降级回复，不暴露系统错误

---

## 11. 分阶段 MVP 实施计划（预览）

| 阶段 | 内容 | 可演示内容 |
|------|------|-----------|
| **Phase 1** | PostgreSQL 数据模型 + FastAPI CRUD + JWT Auth + pytest | Swagger UI 调所有接口，数据库全量建表 |
| **Phase 2** | B端 React 后台（前台工位 + 店长大盘） | 房态格子图、开房退房、工单看板 |
| **Phase 3** | C端 Flutter App（登录 + 控房 + 工单 + 账单） | 完整住客端流程 |
| **Phase 4** | AI 引擎（LangGraph + Tool Calling + RAG + Guard） | AI 管家对话、Prompt 注入防御 |
| **Phase 5** | WebSocket 实时推送 + 管理沙盒模拟器 + 定时审计 | 端到端实时联动演示 |

---

> 本文档为 SmartStay 项目唯一设计事实来源，后续实施严格按照此文档执行。
