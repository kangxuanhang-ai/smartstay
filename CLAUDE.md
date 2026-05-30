    # CLAUDE.md

    This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

    ## Project Overview

    SmartStay (智宿云) is an AI-powered full-stack hotel management system with three clients sharing one FastAPI backend:

    | Component | Stack | Directory |
    |-----------|-------|-----------|
    | **C-end (Guest)** | Flutter 3.35+ / BLoC / GoRouter / Dio | `smartstay-flutter/` (separate git repo) |
    | **B-end (Staff)** | React 19 / TypeScript / Vite / Ant Design / Zustand | `frontend/` |
    | **Backend** | FastAPI / SQLModel / PostgreSQL / pgvector / LangGraph | `backend/` |

    ## Running the Project

    ### Backend (required first)
    ```bash
    cd backend
    poetry install
    # Ensure PostgreSQL is running with pgvector extension
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    Auto-seeds default data on startup (users, rooms, hotel info). Default password for all seeded users: `123456`.

    ### Frontend B-end
    ```bash
    cd frontend
    npm install
    npm run dev   # port 5173
    ```

    ### Flutter C-end
    ```bash
    cd smartstay-flutter
    flutter pub get
    flutter run
    ```
    Configure backend IP in `lib/core/config.dart` (copy from `config.example.dart`).

    ## Architecture

    ### Backend Structure
    - `app/api/` — REST route handlers (auth, rooms, orders, work_orders, consumptions, hotel, ai, rag, admin)
    - `app/ai/` — LangGraph agent: graph.py (state graph), tools.py (4 tools), guard.py (security), rag.py (vector search), pricing.py (dynamic pricing)
    - `app/models/` — SQLModel ORM (15 tables: guests, staff, rooms, orders, work_orders, consumptions, invoice_records, chat_sessions, chat_messages, ai_pricing_logs, audit_reports, ai_security_logs, rag_documents, rag_embeddings, hotel_info, facilities)
    - `app/schemas/` — Pydantic request/response schemas
    - `app/core/` — config.py (env), database.py (engine), deps.py (auth dependencies), security.py (JWT/bcrypt), seed.py (default data)
    - `app/ws/` — WebSocket ConnectionManager (real-time push)
    - `app/tasks/` — APScheduler audit report generation (4 AM daily)

    ### Key Backend Patterns
    - **Dual user model**: `Guest` (C-end) and `Staff` (B-end) are separate tables. JWT tokens carry `user_type` claim.
    - **Auth endpoints**: `/api/auth/login` (guest), `/api/auth/login/biz` (staff), `/api/auth/change-password`, `/api/auth/me`
    - **RBAC**: `require_role()` dependency in `deps.py` enforces role-based access
    - **AI agent**: LangGraph StateGraph with 3 branches — chat (conversation), knowledge (RAG), action (tool calling). Intent classification via LLM with keyword fallback.
    - **Security guard**: `guard.py` intercepts all tool calls — enforces price caps (50%), temperature range (16-30°C), work order limits (5/room)
    - **RAG**: fastembed (BAAI/bge-small-zh-v1.5, 512-dim) + pgvector cosine similarity, threshold > 0.1
    - **WebSocket**: JWT-authenticated, supports send_to_user, broadcast_to_role, broadcast_biz, send_to_room

    ### Frontend B-end Structure
    - `src/pages/front-desk/` — RoomGridPage, CheckInModal, WorkOrderBoard, AIPricingAlert, NewWorkOrderAlert
    - `src/pages/manager/` — DashboardPage (ECharts), AIAuditPage, KnowledgeBasePage, UserManagementPage, InvoiceManagementPage
    - `src/pages/admin/` — AdminPage (simulation sandbox)
    - `src/stores/authStore.ts` — Zustand auth state with localStorage token persistence
    - `src/hooks/useWebSocket.ts` — Singleton WebSocket with pub/sub and auto-reconnect
    - `src/api/client.ts` — Axios with JWT interceptors and auto-refresh on 401

    ### Flutter C-end Structure
    - `lib/blocs/` — BLoC state management: auth, room, chat, work_order
    - `lib/pages/` — 9 pages: home, login, change_password, room_control, ai_chat, work_order, bill, my, facility, map
    - `lib/widgets/` — LoginBottomSheet (bottom sheet login), AuthPrompt (unauth overlay), BottomNav
    - `lib/core/` — api_client.dart (Dio singleton with token interceptor), config.dart, sse_parser.dart, ws_service.dart
    - `lib/app.dart` — GoRouter config with role-based redirect

    ## Database

    PostgreSQL with pgvector. Connection: `postgres:postgres@localhost:5432/smartstay`

    Prices stored in **cents (fen)**. Room device_states stored as JSONB. UUID primary keys throughout.

    See `DATABASE_RELATIONS.md` for full schema documentation.

    ## Testing

    ```bash
    cd backend
    pytest                    # all tests
    pytest tests/test_auth.py # single file
    pytest -k "test_name"     # single test
    ```

    Uses pytest-asyncio with `ASGITransport` for in-process testing. Fixtures: `client`, `biz_token`, `guest_token`.

    ## Environment Variables

    Backend requires `.env` with: `DATABASE_URL`, `DATABASE_URL_SYNC`, `SECRET_KEY`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`

    ## Design Documents

    - `1. SmartStay-Agent.md` — Full product specification
    - `DATABASE_RELATIONS.md` — Database schema and relationships
    - `docs/superpowers/specs/` — Design specifications
    - `docs/superpowers/plans/` — Implementation plans
    - `rag_docs/` — RAG knowledge base source documents
