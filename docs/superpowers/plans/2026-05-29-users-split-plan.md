# users 表拆分实施计划

> **Goal:** 将单一 `users` 表拆分为 `guests`（住客）+ `staff`（工作人员）双表

**Architecture:** 新建 Guest 模型，User 重命名为 Staff，JWT 加 user_type 字段区分查询哪张表

**Tech Stack:** FastAPI, SQLModel, PostgreSQL, python-jose

---

## Task 1: 新建 Guest 模型 + User→Staff 改名

**Files:**
- Create: `backend/app/models/guest.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建 `backend/app/models/guest.py`**
- [ ] **Step 2: 将 `backend/app/models/user.py` 中 User 改为 Staff（表名 users→staff，去掉 is_active，去掉 role 默认值）**
- [ ] **Step 3: 更新 `backend/app/models/__init__.py` 导出 Guest 和 Staff**

## Task 2: 更新 FK 引用

**Files:**
- Modify: `backend/app/models/order.py` — FK users.id → guests.id
- Modify: `backend/app/models/ai_log.py` — FK users.id → staff.id
- Modify: `backend/app/models/rag.py` — FK users.id → staff.id
- Modify: `backend/app/models/security_log.py` — 去掉 FK，新增 user_type 字段

- [ ] **Step 1-4: 逐个修改 FK**

## Task 3: 更新 database.py + security.py

**Files:**
- Modify: `backend/app/core/database.py` — init_db 加 drop users 表
- Modify: `backend/app/core/security.py` — JWT 创建函数保持不变（调用方传 user_type）

- [ ] **Step 1: database.py 加 drop users**
- [ ] **Step 2: security.py 无需改（调用方传 user_type 即可）**

## Task 4: 更新 deps.py

**Files:**
- Modify: `backend/app/core/deps.py` — get_current_user 双表查询 + require_role 适配 Guest

- [ ] **Step 1: 重写 get_current_user 和 require_role**

## Task 5: 更新 seed.py

**Files:**
- Modify: `backend/app/core/seed.py` — 拆成 seed_guests + seed_staff

- [ ] **Step 1: 拆分 DEFAULT_USERS → DEFAULT_STAFF + DEFAULT_GUESTS**

## Task 6: 更新 auth.py

**Files:**
- Modify: `backend/app/api/auth.py` — c_login 查 guests，b_login 查 staff，refresh 用 user_type

- [ ] **Step 1: 重写所有登录端点**

## Task 7: 更新 orders.py

**Files:**
- Modify: `backend/app/api/orders.py` — check_in/checkout/get_active_order 查 Guest

- [ ] **Step 1: 将 User 引用改为 Guest**

## Task 8: 更新 work_orders.py + admin.py

**Files:**
- Modify: `backend/app/api/work_orders.py` — get_staff_list 查 Staff
- Modify: `backend/app/api/admin.py` — 用户管理分表

- [ ] **Step 1-2: 更新两个文件**

## Task 9: 更新剩余 API import

**Files:**
- Modify: `backend/app/api/rooms.py`, `consumptions.py`, `ai.py`, `rag.py`

- [ ] **Step 1: 替换 import User → Guest/Staff**

## Task 10: 更新测试 + 前端

**Files:**
- Modify: `backend/tests/conftest.py`, `test_auth.py`, `test_orders.py`, `test_rooms.py`, `test_work_orders.py`
- Modify: `frontend/src/pages/manager/UserManagementPage.tsx`

- [ ] **Step 1: 更新测试**
- [ ] **Step 2: 更新前端**

## Task 11: 运行测试验证

- [ ] **Step 1: `poetry run pytest tests/ -v` 全部通过**
