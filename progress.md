# SmartStay — Progress Log

## Current Status

**Phase**: Core build complete, refinement/features ongoing
**Last verified**: 2026-05-30
**Backend**: ✅ Running (FastAPI + PostgreSQL + pgvector)
**B-end Frontend**: ✅ Running (React 19 + Ant Design 6)
**C-end Flutter**: ✅ Running (Flutter 3.35+ / BLoC)

## What's Done

### F001 — Backend Core (2026-05-23)
- FastAPI server with 15 SQLModel tables
- Dual user model (Guest + Staff) with JWT auth (access 15min + refresh 7d)
- ~40 API endpoints across 8 route modules
- WebSocket manager for real-time push
- Seed data: 7 staff + 2 guests + 10 rooms + hotel info + 4 facilities

### F002 — B-end React Frontend (2026-05-23)
- Login with role-based redirect
- Room grid with color-coded status + context menu
- Check-in modal, room detail modal
- Kanban work order board with assignment
- Manager dashboard (KPIs, ECharts)
- Knowledge base management (RAG upload)
- User management (staff CRUD)
- Invoice management
- Admin sandbox (simulations + reset)

### F003 — C-end Flutter App (2026-05-23)
- 11 pages: home, login, change-password, room-control, ai-chat, work-orders, my, bill, bill-detail, map, facility
- 4 BLoCs: auth, chat (dual-platform SSE), room (debounced IoT), work-order (WebSocket auto-refresh)
- Dio client with JWT refresh interceptor
- WebSocket singleton with auto-reconnect

### F004 — AI Engine (2026-05-23)
- LangGraph StateGraph: classify → chat/knowledge/action
- 4 tools: control_device, create_work_order, query_knowledge, modify_room_price
- Security guard: role checks, temp bounds (16-30°C), price cap (50%), work order limit (5/room)
- RAG: fastembed bge-small-zh-v1.5 (512-dim) + pgvector cosine similarity
- Pricing agent (standalone, manager approval flow)
- Audit agent (APScheduler daily 4AM)

### F005 — Users Table Split (2026-05-30)
- `users` table dropped, replaced by `guests` + `staff`
- JWT `user_type` claim distinguishes guest vs staff
- `get_current_user` dependency resolves from correct table
- All API routes, seed data, and frontend updated

### F009 — UTC → 中国标准时间 (2026-05-30)
- 新建 `backend/app/core/utils.py`: `cst_now()` + `cst_isoformat()`
- 12 个模型文件 `default_factory=datetime.utcnow` → `cst_now()`
- 6 个 API 文件 `datetime.utcnow()` → `cst_now()`
- 4 个 AI 模块 `datetime.utcnow()` → `cst_now()`
- 1 个审计任务 `datetime.utcnow()` → `cst_now()`
- 2 个 schema 文件加 `field_serializer` 输出 `+08:00` 后缀
- 所有 `.isoformat()` 手动序列化 → `cst_isoformat()`
- Flutter C 端 `DateTime.tryParse()` 加 `.toLocal()`
- B 端 `RoomGridPage` 去掉 `'Z'` 后缀

### F010 — Bug Fixes (2026-05-30)

**B001: 用户管理看不到C端住客数据**
- 根因：前端 `role=guest` → 后端走 Staff 表查询，查不到 Guest
- 修复：`UserManagementPage.tsx` 改为 `type=guest`
- 验证：API `/api/admin/users?type=guest` 返回住客数据 ✅

**B002: C端首次登录改密后没反应**
- 根因：GoRouter redirect 在 LoginBottomSheet 改密前跳转 `/change-password`，弹窗被关闭
- 修复：`app.dart` 移除 `passwordChangeRequired` 自动跳转；`change_password_page.dart` 加 `context.go('/home')`
- 验证：dart analyze 通过 ✅

### F011 — C-end Homepage Redesign (2026-05-30)
- 完全重写 `home_page.dart` (498 insertions, 64 deletions)
- 5个区块: Banner渐变 → 欢迎卡片(登录后) → 酒店亮点2x2 → 设施列表(色条) → 底部信息
- 渐变Banner: #1A1A2E → #1677FF, 酒店名+标语+导航/拨号按钮
- 欢迎卡片: 用户名+房间信息(API获取)+4个快捷入口
- 亮点卡片: AI管家/机器人送物/智能客房/空中花园, 点击拦截登录
- 设施卡片: 4px彩色左条, 按设施类型着色
- dart analyze 0 issues, 已提交

## What's Next

### F014 — C 端 AI 聊天增强 (done)
- Spec: `docs/superpowers/specs/2026-06-02-c-end-ai-chat-enhancement-design.md`
- Plan: `docs/superpowers/plans/2026-06-02-c-end-ai-chat-enhancement-plan.md`
- 12 tasks across 3 phases, all completed (2026-06-02)
- Phase 1 (UX): stop/cancel button, typing indicator, tool call loading status, quick action chips
- Phase 2 (Features): Markdown rendering, interactive cards, multi-session history (backend + frontend)
- Phase 3 (Refactor): SSEStreamHandler, ChatCard model, ChatStreamService + ChatBloc split
- Voice input (阿里云 ASR) deferred to follow-up
- New files: typing_indicator.dart, quick_chips.dart, chat_card.dart (widget + model), session_list_page.dart, sse_stream_handler.dart, chat_stream_service.dart
- Backend: GET /api/ai/chat/sessions endpoint added

### F006 — C-end Navigation Redesign (planned)
- Spec: `docs/superpowers/specs/2026-05-29-c-end-navigation-redesign-design.md`
- Plan: `docs/superpowers/plans/2026-05-29-c-end-navigation-redesign-plan.md`
- 9 tasks: LoginBottomSheet, AuthPrompt, page-level auth, My page, bill detail, bottom nav

## Evidence Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-30 | Harness created | CLAUDE.md, feature_list.json, progress.md, init.sh, session-handoff.md |
