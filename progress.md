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

## What's Next

### F006 — C-end Navigation Redesign (planned)
- Spec: `docs/superpowers/specs/2026-05-29-c-end-navigation-redesign-design.md`
- Plan: `docs/superpowers/plans/2026-05-29-c-end-navigation-redesign-plan.md`
- 9 tasks: LoginBottomSheet, AuthPrompt, page-level auth, My page, bill detail, bottom nav

## Evidence Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-30 | Harness created | CLAUDE.md, feature_list.json, progress.md, init.sh, session-handoff.md |
