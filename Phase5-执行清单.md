# Phase 5 执行清单：WebSocket 实时推送 + 审计定时任务 + 管理沙盒

> 按 Spec 和 Design Doc 逐条对照，不简写，不偷懒。

---

## 第一组：后端 WebSocket 基础设施（新建 1 文件，修改 1 文件）

| # | 文件 | Spec 对应 | 内容 |
|---|------|----------|------|
| 1 | `backend/app/ws/manager.py`（新建） | Spec 4.1「WebSocket 双向实时网关」、Design 4「连接管理」 | **ConnectionManager 类**：① `active_connections: dict[str, list[WebSocket]]` — user_id → WebSocket 列表映射 ② `async connect(websocket, token)` — 校验 JWT 的 `sub` + `role` → 存入字典 → 返回 user_id/role ③ `disconnect(user_id, websocket)` — 从列表移除 → 空则删 key ④ `async send_to_user(user_id, message)` — 遍历该用户的 WebSocket 列表逐一 `send_json` ⑤ `async broadcast_to_role(role, message)` — 遍历所有该角色的连接广播 ⑥ `async broadcast_biz(message)` — 广播给所有 B端连接（front_desk + manager + admin）⑦ `async send_to_room(room_id, message)` — 通过 room_id 找到住客 user_id → 推送 |
| 2 | `backend/app/main.py`（修改） | Spec 4.1 | 注册 `@app.websocket("/ws")` 端点：① 从 `websocket.query_params` 获取 JWT token ② 调用 `manager.connect(websocket, token)` ③ 进入 `while True` 循环接收消息（保活）④ except → `manager.disconnect(user_id, websocket)` |

## 第二组：WebSocket 事件推送 — 后端 API 层注入（修改 2 文件）

| # | 文件 | Spec 对应 | 内容 |
|---|------|----------|------|
| 3 | `backend/app/api/work_orders.py`（修改） | Spec 3.1「WebSocket 客服工单流看板」、Design 4 `work_order.new` | **创建工单后推送 B端**：`POST /api/work-orders/` 成功创建后 → `await manager.broadcast_biz({"event": "work_order.new", "data": {"order_id": str(wo.id), "room_number": "...", "type": wo.type, "content": wo.content}})` |
| 4 | `backend/app/api/work_orders.py`（修改） | Spec 3.1「WebSocket 推送 C端」、Design 4 `work_order.status_change` | **接单推 C端**：`PUT /{wo_id}/accept` → `await manager.send_to_user(guest_user_id, {"event": "work_order.status_change", "data": {"order_id": wo_id, "new_status": "accepted", "message": "前台已接单"}})` |
| 5 | `backend/app/api/work_orders.py`（修改） | Spec 3.1 | **指派推 C端**：`PUT /{wo_id}/assign` → `await manager.send_to_user(guest_user_id, {"event": "work_order.status_change", "data": {"order_id": wo_id, "new_status": "processing", "message": f"保洁{assigned_resource}处理中"}})` |
| 6 | `backend/app/api/work_orders.py`（修改） | Spec 3.1「核销 → WebSocket 推 C端」 | **核销完成推 C端**：`PUT /{wo_id}/complete` 成功后 → 根据 `wo.room_id` 找到当前住客的 user_id → `await manager.send_to_user(user_id, {"event": "work_order.status_change", "data": {"order_id": wo_id, "new_status": "completed", "message": "工单已完成/已送达"}})` |
| 7 | `backend/app/api/orders.py` + `backend/app/api/rooms.py`（修改） | Spec 3.1「实时房态全景格子图」、Design 4 `room.status_change` | **房态变更推 B端**：`PUT /api/orders/{id}/checkout` 或 `PUT /api/rooms/{id}/status` 后 → `await manager.broadcast_biz({"event": "room.status_change", "data": {"room_id": id, "old_status": old, "new_status": new}})` |
| 8 | `backend/app/ai/pricing.py`（修改） | Spec 3.1「AI 收益定价人机协同卡点」、Design 4 `ai_pricing.suggestion` | **AI 定价推 B端**：`trigger_pricing_agent()` 成功 INSERT 后 → `await manager.broadcast_biz({"event": "ai_pricing.suggestion", "data": {"log_id": str(log.id), "room_type": room_type, "original": original, "suggested": suggested, "reason": trigger_reason}})` |

## 第三组：B端前端 WebSocket 集成（新建 1 文件，修改 2 文件）

| # | 文件 | Spec 对应 | 内容 |
|---|------|----------|------|
| 9 | `frontend/src/hooks/useWebSocket.ts`（新建） | Spec 3.1「WebSocket 客服工单流看板」 | **WebSocket Hook**：① 组件挂载时 `new WebSocket('ws://localhost:8000/ws?token=...')` ② `onmessage` 解析 JSON → 根据 `event` 类型分发 ③ 组件卸载时 `ws.close()` |
| 10 | `frontend/src/pages/front-desk/WorkOrderBoard.tsx`（修改） | Spec 3.1「前台页面无需刷新，通过 WebSocket 伴随系统提示音秒级弹窗提示」 | **监听 `work_order.new` 事件**：① 收到新工单 → `notification.info()` 弹出提示 ② 播放系统提示音（`new Audio('/notification.mp3').play()` 或 `message.info()` 弹窗）③ 自动刷新工单列表 `fetchOrders()` |
| 11 | `frontend/src/pages/front-desk/AIPricingAlert.tsx`（修改） | Spec 3.1「前台屏幕弹出阻断式高亮弹窗」 | **监听 `ai_pricing.suggestion` 事件**：① WebSocket 收到定价事件 → `setShowAlert(true)` + `setPricingData(...)` ② 弹出 AIPricingAlert 阻断式弹窗 |

## 第四组：C端 Flutter WebSocket 集成（修改 2 文件）

| # | 文件 | Spec 对应 | 内容 |
|---|------|----------|------|
| 12 | `smartstay-flutter/lib/blocs/work_order/work_order_bloc.dart`（修改） | Spec 2.3「纯靠 WebSocket 长连接实时局部刷新状态」 | **WebSocket 连接**：① `initState` 时通过 `web_socket_channel` 包连接 `ws://172.20.10.8:8000/ws?token=...` ② `channel.stream.listen(...)` 监听 `work_order.status_change` 事件 ③ 收到推送 → `add(WorkOrdersFetched())` 重新拉取工单列表 ④ `close()` 时 `channel.sink.close()` |
| 13 | `smartstay-flutter/lib/blocs/work_order/work_order_bloc.dart`（修改） | Spec 2.3 | **双模式切换**：① 移动端：WebSocket 保持长连接 ② Web 端：降级为 HTTP 轮询（每 10 秒拉一次） |

## 第五组：审计定时任务注册（修改 1 文件 + 安装依赖）

| # | 文件 | Spec 对应 | 内容 |
|---|------|----------|------|
| 14 | `poetry add apscheduler` | — | 安装 APScheduler 依赖 |
| 15 | `backend/app/main.py`（修改） | Spec 3.2「凌晨 4:00 的定时任务」 | **APScheduler 定时任务**：① 在 `lifespan` 中注册：`scheduler.add_job(generate_audit_report, 'cron', hour=4, minute=0)` ② 每天凌晨 4:00 自动调用 `app.tasks.audit.generate_audit_report()` ③ 关闭时 `scheduler.shutdown()` |
| 16 | `backend/app/main.py`（修改） | Spec 3.2 | **启动时立即执行一次**：首次启动后延迟 30 秒执行一次审计，生成首份报告 |

## 第六组：管理沙盒完善（修改 2 文件）

| # | 文件 | Spec 对应 | 内容 |
|---|------|----------|------|
| 17 | `backend/app/api/admin.py` `simulate_door_open`（修改） | Spec 3.3「模拟门锁打开」 | 修复数据不一致：`order.status = "checked_in"` → 同时更新 `rooms.status = "occupied"` |
| 18 | `frontend/src/pages/admin/AdminPage.tsx`（修改） | Spec 3.3 | 安全日志表格加**自动刷新**：每次调用模拟 Prompt 注入后自动 `fetchLogs()` |

## 第七组：端到端联调验证（手动执行）

| # | 操作 | 验收 |
|---|------|------|
| 19 | 后端启动 + B端启动 + C端启动 | 无报错 |
| 20 | C端 AI 管家说「送两双拖鞋」→ 工单创建 | B端工单看板自动出现新工单弹窗 + 提示音 |
| 21 | B端前台接单 → 指派张阿姨 → 确认完成 | C端工单时间轴逐级更新，无需刷新 |
| 22 | 管理员沙盒 → 模拟门锁打开 | 订单推进 + 房态变更 → B端房态格子图实时变色 |
| 23 | 凌晨审计定时任务 | 启动后 30 秒自动执行 → `audit_reports` 表有数据 → B端 AI 审计页显示报告 |

## 验证清单

| # | 操作 |
|---|------|
| 24 | `poetry run python -m pytest tests/` → 18 通过 |
| 25 | `npx tsc --noEmit` → 前端零错误 |
| 26 | `dart analyze lib/` → Flutter 零错误 |
| 27 | `flutter build web` → 构建成功 |

---

## 文件变更汇总

| 类型 | 数量 | 文件 |
|------|------|------|
| **新建** | 2 | `backend/app/ws/manager.py`、`frontend/src/hooks/useWebSocket.ts` |
| **修改** | 10 | `backend/app/main.py`、`backend/app/api/work_orders.py`、`backend/app/api/orders.py`、`backend/app/api/rooms.py`、`backend/app/api/admin.py`、`backend/app/ai/pricing.py`、`frontend/src/pages/front-desk/WorkOrderBoard.tsx`、`frontend/src/pages/front-desk/AIPricingAlert.tsx`、`frontend/src/pages/admin/AdminPage.tsx`、`smartstay-flutter/lib/blocs/work_order/work_order_bloc.dart` |

**共 7 组，27 个步骤，新建 2 个文件，修改 10 个文件。**
