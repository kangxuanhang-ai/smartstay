# users 表拆分设计规格说明书

> 将单一 `users` 表拆分为 `guests`（住客）+ `staff`（工作人员）双表，消除角色混杂的设计异味。

---

## 1. 背景与目标

### 1.1 问题

当前 `users` 表用一个 `role` 字段区分住客（guest）、前台（front_desk）、保洁（housekeeping）、维修（maintenance）、店长（manager）、管理员（admin）六种人。这导致：

- 住客和员工混在同一张表，查询时需要 `WHERE role = 'xxx'` 过滤
- 保洁/维修人员实际上是 `role="front_desk"` + `staff_type` 区分，设计不直观
- `is_active` 字段对员工没有意义（只有住客需要退房停用）
- 表越来越大，概念边界模糊

### 1.2 目标

- 将住客拆到 `guests` 表，员工拆到 `staff` 表
- 保持所有业务逻辑不变（状态机、工单流程、AI 引擎、WebSocket 推送）
- 保持 API 响应格式不变，前端和 Flutter 尽可能少改
- 保持测试通过

---

## 2. 数据模型变更

### 2.1 新建 `guests` 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| id_card | VARCHAR(18) | UNIQUE, NOT NULL | 身份证号 |
| phone | VARCHAR(11) | NOT NULL | 手机号 |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt 密码 |
| is_first_login | BOOLEAN | DEFAULT TRUE | 首次登录强制改密 |
| is_active | BOOLEAN | DEFAULT TRUE | 退房后设为 False |
| created_at | TIMESTAMP | DEFAULT NOW() | — |

**无 `role` 字段**：住客永远是住客，不需要角色区分。

### 2.2 改造 `users` → `staff` 表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK | 主键 |
| id_card | VARCHAR(18) | UNIQUE, NOT NULL | 身份证号/工号 |
| phone | VARCHAR(11) | NOT NULL | 手机号 |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| hashed_password | VARCHAR(255) | NOT NULL | bcrypt 密码 |
| is_first_login | BOOLEAN | DEFAULT TRUE | 首次登录强制改密 |
| role | VARCHAR(20) | NOT NULL | front_desk / manager / admin |
| staff_type | VARCHAR(20) | NULLABLE | housekeeping / maintenance（仅 role=front_desk 时使用） |
| created_at | TIMESTAMP | DEFAULT NOW() | — |

**变化点**：
- 表名 `users` → `staff`
- 去掉 `is_active`（员工不需要退房停用逻辑）
- `role` 不再有 `"guest"` 值，只保留 `front_desk` / `manager` / `admin`
- `staff_type` 继续保留，用于区分前台接待 vs 保洁 vs 维修

### 2.3 外键变更

| 表 | 字段 | 原 FK | 新 FK | 说明 |
|----|------|-------|-------|------|
| orders | user_id | users.id | **guests.id** | 只有住客下订单 |
| ai_pricing_logs | confirmed_by | users.id | **staff.id** | 只有店长审批 |
| rag_documents | uploaded_by | users.id | **staff.id** | 只有店长上传 |
| ai_security_logs | user_id | users.id | **去掉 FK** | 住客/员工都可能触发 |
| ai_security_logs | *(新增)* | — | **user_type: VARCHAR(20)** | 'guest' 或 'staff'，用于标识 user_id 指向哪张表 |

### 2.4 不变的表

rooms, work_orders, consumptions, invoice_records, audit_reports, chat_sessions, chat_messages, hotel_info, facilities, rag_embeddings — 全部不动。

---

## 3. JWT 变更

### 3.1 Token Payload

```json
// 住客登录
{"sub": "uuid", "role": "guest", "user_type": "guest"}

// 员工登录
{"sub": "uuid", "role": "front_desk", "user_type": "staff"}
```

新增 `user_type` 字段，值为 `"guest"` 或 `"staff"`，用于 `get_current_user` 和 `refresh_token` 知道查哪张表。

### 3.2 端点变化

| 端点 | 变化 |
|------|------|
| `POST /api/auth/login` | 查 `guests` 表 WHERE `id_card` AND `role` 无关 |
| `POST /api/auth/login/biz` | 查 `staff` 表 WHERE `id_card` AND `role` IN (`front_desk`, `manager`, `admin`) |
| `POST /api/auth/refresh` | 读 JWT `user_type` → 查对应表 |
| `POST /api/auth/change-password` | `get_current_user` 返回的对象已经是正确表的实例 |
| `GET /api/auth/me` | 住客返回 `{..., "role": "guest"}`，员工返回 `{..., "role": staff.role}` |

---

## 4. 依赖注入层变更

### 4.1 `get_current_user`

```python
async def get_current_user(...) -> Guest | Staff:
    payload = decode_token(token)
    user_type = payload.get("user_type")
    user_id = uuid.UUID(payload.get("sub"))
    
    if user_type == "guest":
        result = await db.execute(select(Guest).where(Guest.id == user_id, Guest.is_active == True))
    else:
        result = await db.execute(select(Staff).where(Staff.id == user_id))
    
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

### 4.2 `require_role`

```python
def require_role(*roles: str):
    async def role_checker(current_user: Guest | Staff = Depends(get_current_user)) -> Guest | Staff:
        if isinstance(current_user, Guest):
            if "guest" not in roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        else:
            if current_user.role not in roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker
```

---

## 5. API 层变更

### 5.1 `orders.py` — 前台开房/退房

**开房（check_in）**：
- 查/建对象从 `User` → `Guest`
- `Guest` 没有 `role` 字段，不需要设置 `role="guest"`

**退房（checkout）**：
- 查 `Guest` 表设 `is_active=False`

**查住客信息（get_active_order_by_room）**：
- 查 `Guest` 表获取住客姓名等信息

### 5.2 `work_orders.py` — 工单指派

**get_staff_list**：
- 查 `Staff` 表 WHERE `role="front_desk"` AND `staff_type IS NOT NULL`
- 逻辑不变，只是表名变了

### 5.3 `admin.py` — 管理后台

| 功能 | 改动 |
|------|------|
| `list_users` | 新增 `type` 参数（`guest`/`staff`），分别查 `Guest` 或 `Staff` 表 |
| `create_user` | 创建 `Staff` 对象（B 端不创建住客） |
| `seed_mock_data` | 住客用 `Guest(...)` 创建 |
| `reset_data` | 同时 truncate `guests` 和 `staff`，然后 re-seed |
| `simulate_prompt_inject` | `AISecurityLog` 新增 `user_type="guest"` |

### 5.4 其他 API 文件

| 文件 | 改动 |
|------|------|
| `rooms.py` | 只改 import，业务逻辑不变 |
| `consumptions.py` | 只改 import |
| `ai.py` | 只改 import，`confirmed_by` 指向 `staff.id` |
| `rag.py` | 只改 import，`uploaded_by` 指向 `staff.id` |

### 5.5 不需要改的文件

| 文件 | 原因 |
|------|------|
| `ws/manager.py` | 不直接查 users 表，role 从 JWT 读取 |
| `ai/guard.py` | 不直接查 users 表 |
| `ai/graph.py` | role 从 AgentState 读取 |
| `ai/tools.py` | 不直接查 users 表 |
| `ai/rag.py` | 不直接查 users 表 |
| `tasks/audit.py` | 不直接查 users 表 |

---

## 6. 前端变更

### 6.1 React B端

| 文件 | 改动 |
|------|------|
| `authStore.ts` | `User` 接口不变（`role` 字段保留，Guest 的 role 固定为 `"guest"`） |
| `AppLayout.tsx` | 不变 |
| `LoginPage.tsx` | 不变 |
| `UserManagementPage.tsx` | "员工" tab 调 `?type=staff`，"住客" tab 调 `?type=guest` |
| 其他页面 | 不变 |

**API 响应格式不变**，前端不需要大改。

### 6.2 Flutter C端

**不需要改任何代码** — API 响应格式不变。

---

## 7. Seed 数据变更

```python
DEFAULT_STAFF = [
    {"id_card": "dianzhang", "phone": "13800000001", "name": "总店长", "role": "manager"},
    {"id_card": "qiantai", "phone": "13800000002", "name": "前台张", "role": "front_desk"},
    {"id_card": "admin", "phone": "13800000003", "name": "管理员", "role": "admin"},
    {"id_card": "bj001", "phone": "13800000004", "name": "张阿姨", "role": "front_desk", "staff_type": "housekeeping"},
    {"id_card": "bj002", "phone": "13800000005", "name": "李阿姨", "role": "front_desk", "staff_type": "housekeeping"},
    {"id_card": "wx001", "phone": "13800000006", "name": "王师傅", "role": "front_desk", "staff_type": "maintenance"},
    {"id_card": "wx002", "phone": "13800000007", "name": "赵师傅", "role": "front_desk", "staff_type": "maintenance"},
]

DEFAULT_GUESTS = [
    {"id_card": "13042920030603401X", "phone": "13800000101", "name": "康烜航"},
    {"id_card": "100000000000000101", "phone": "13800000102", "name": "住客李"},
]
```

---

## 8. 测试变更

| 改动 | 说明 |
|------|------|
| `conftest.py` | `guest_token` fixture 调 `/api/auth/login`（查 guests 表），`biz_token` 不变 |
| `test_auth.py` | 断言中的表名变化，登录端点不变 |
| `test_orders.py` | check_in 创建的用户现在在 guests 表 |
| `test_rooms.py` | 基本不变 |
| `test_work_orders.py` | 基本不变 |

---

## 9. 数据库迁移

当前使用 `SQLModel.metadata.create_all`，无 Alembic。迁移策略：

1. `init_db()` 中先 `DROP TABLE IF EXISTS users CASCADE`（旧表）
2. 然后 `create_all` 创建 `guests` 和 `staff` 新表
3. 启动后 seed 脚本重新注入默认数据

**注意**：这是破坏性迁移，旧数据会丢失。由于是开发阶段的演示项目，可接受。

---

## 10. 文件变更汇总

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/guest.py` | 新建 | Guest SQLModel |
| `backend/app/models/user.py` | 重写 | User → Staff |
| `backend/app/models/order.py` | 修改 | FK → guests.id |
| `backend/app/models/ai_log.py` | 修改 | FK → staff.id |
| `backend/app/models/rag.py` | 修改 | FK → staff.id |
| `backend/app/models/security_log.py` | 修改 | 去 FK + 新增 user_type |
| `backend/app/models/__init__.py` | 修改 | Guest, Staff 导出 |
| `backend/app/core/database.py` | 修改 | init_db 加 drop users |
| `backend/app/core/deps.py` | 修改 | get_current_user 双表查询 |
| `backend/app/core/seed.py` | 修改 | 拆成两个 seed 函数 |
| `backend/app/schemas/auth.py` | 修改 | 响应加 user_type（可选） |
| `backend/app/api/auth.py` | 修改 | 登录分表查询 |
| `backend/app/api/orders.py` | 修改 | check_in/checkout 改查 Guest |
| `backend/app/api/work_orders.py` | 修改 | get_staff_list 改查 Staff |
| `backend/app/api/admin.py` | 修改 | 用户管理分表 |
| `backend/app/api/rooms.py` | 修改 | import 变更 |
| `backend/app/api/consumptions.py` | 修改 | import 变更 |
| `backend/app/api/ai.py` | 修改 | import 变更 |
| `backend/app/api/rag.py` | 修改 | import 变更 |
| `backend/tests/conftest.py` | 修改 | fixture 调整 |
| `backend/tests/test_auth.py` | 修改 | 断言调整 |
| `backend/tests/test_orders.py` | 修改 | 断言调整 |
| `backend/tests/test_rooms.py` | 微调 | import 变更 |
| `backend/tests/test_work_orders.py` | 微调 | import 变更 |
| `frontend/src/pages/manager/UserManagementPage.tsx` | 微调 | API 参数变化 |

**不需要改的文件**：`ws/manager.py`, `ai/guard.py`, `ai/graph.py`, `ai/tools.py`, `ai/rag.py`, `tasks/audit.py`, `frontend` 其他文件, `smartstay-flutter/` 全部文件。

---

> 本文档为 users 表拆分的唯一设计事实来源。
