# SmartStay (智宿云) — Agent Instructions

AI-powered hotel management system. Three clients, one FastAPI backend.

## Quick Start

```bash
# Backend (requires PostgreSQL with pgvector + .env with DEEPSEEK_API_KEY)
cd backend && poetry install && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# B-end frontend
cd frontend && npm install && npm run dev          # -> http://localhost:5173

# C-end Flutter (set backend IP in lib/core/config.dart first)
cd smartstay-flutter && flutter pub get && flutter run
```

## Directory Layout

```
backend/            FastAPI + SQLModel + LangGraph + pgvector
  app/api/          Route handlers (auth, rooms, orders, work_orders, ai, rag, admin, hotel, consumptions)
  app/models/       SQLModel table definitions (15 tables)
  app/core/         Config, DB engine, auth/security, deps, seed data
  app/ai/           LangGraph agent (graph, tools, guard, rag, state, pricing)
  app/ws/           WebSocket connection manager
  app/tasks/        APScheduler cron jobs (audit agent)
frontend/           React 19 + TS + Ant Design 6 + Zustand + ECharts
  src/pages/        3 role sections: front-desk/, manager/, admin/
  src/stores/       Zustand authStore (single store)
  src/hooks/        useWebSocket (singleton, pub/sub)
  src/api/          Axios client with 401 auto-refresh
smartstay-flutter/  Flutter 3.35+ / BLoC / GoRouter / Dio
  lib/blocs/        4 BLoCs: auth, chat, room, work_order
  lib/pages/        11 pages across 10 directories
  lib/core/         ApiClient (Dio+JWT refresh), WsService, SSE parser, config
docs/superpowers/   Design specs (specs/) and implementation plans (plans/)
rag_docs/           Hotel service manual (vectorized for RAG knowledge base)
```

## Architecture Invariants

- **Prices in cents (fen)**: All monetary values are integers. `30000` = 300 yuan. Display by dividing by 100.
- **UUID primary keys**: Every table uses `uuid.UUID` with auto-generation.
- **Dual user model**: `Guest` (no role) + `Staff` (front_desk/manager/admin). JWT carries `user_type` claim.
- **AI safety guard**: Every LLM tool call passes through `guard.py` before execution. Room ID is injected server-side, never trusted from LLM output.
- **SSE streaming format**: AI chat returns `text/event-stream` with JSON lines: `{type: "text"|"card"|"done", data: ...}`.
- **WebSocket events**: `room.status_change`, `work_order.new`, `work_order.status_change`, `ai_pricing.suggestion`.
- **500ms debounce**: Device control (lights, curtain, AC) uses debounced POST with optimistic UI.
- **First-login forced password change**: All seeded accounts start with password `123456` and `is_first_login=True`.

## Seed Accounts (password: `123456`)

| ID Card | Role | Purpose |
|---------|------|---------|
| `100000000000000001` | front_desk | 前台接待 |
| `100000000000000002` | front_desk + housekeeping | 客房保洁 |
| `100000000000000003` | front_desk + maintenance | 维修工 |
| `100000000000000004` | manager | 经理 |
| `100000000000000005` | admin | 系统管理员 |
| `200000000000000001` | guest | 住客A |
| `200000000000000002` | guest | 住客B |

## Verification

Run before claiming any task is done:

```bash
# Backend: type check + tests
cd backend && poetry run python -m py_compile app/main.py
cd backend && poetry run pytest -x -q

# Frontend: type check
cd frontend && npx tsc --noEmit

# Flutter: analyze
cd smartstay-flutter && flutter analyze
```

## Key Docs (read before making changes)

- **Full PRD**: `1. SmartStay-Agent.md`
- **Technical spec**: `docs/superpowers/specs/2026-05-23-smartstay-design.md`
- **DB schema + relations**: `DATABASE_RELATIONS.md`
- **Users split design**: `docs/superpowers/specs/2026-05-29-users-split-design.md`
- **C-end nav redesign**: `docs/superpowers/specs/2026-05-29-c-end-navigation-redesign-design.md`

## Workflow Rules

1. **Read the relevant spec before coding.** Each feature has a design doc in `docs/superpowers/specs/` and a plan in `docs/superpowers/plans/`.
2. **One feature at a time.** Update `feature_list.json` when starting/completing.
3. **Run verification before claiming done.** See commands above.
4. **Log evidence in progress.md.** What was changed, what was tested, what passed.
5. **Update session-handoff.md at end of session.** So the next session can resume.
