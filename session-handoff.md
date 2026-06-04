# SmartStay — Session Handoff

## How to Use This File

1. **At end of session**: Fill in the "Last Session" section below with what was done, what's pending, and any blockers.
2. **At start of next session**: Read this file first. Resume from the "Next Steps" listed.

---

## Restart Marker (for quick session resume)

**Last updated**: 2026-06-04
**Active feature**: Web search feature (F018) — code done, pending pip install + manual test
**Next up**: Ask user what to work on next
**Quick command to resume**: Read this file → Install google-search-results → Configure SERPAPI_KEY in backend/.env → Manual test

---

## Last Session

**Date**: 2026-06-03
**Feature**: F017 — AI 智能体三阶段优化
**Goal**: 三阶段优化 SmartStay AI：质量提升 → 偏好记忆 → 投诉自动响应

**What was done**:
- Phase 1 Task 1.1: chat_node prompt 重写（角色小智、回复规范、上下文注入、few-shot）
- Phase 1 Task 1.2: action_node prompt 重写（结构化段落、精简参数表、偏好保存规则）
- Phase 1 Task 1.3: knowledge_node prompt 重写（不编造信息约束）
- Phase 1 Task 1.4: classify_intent 改进（8 few-shot + 政策→knowledge 规则）
- Phase 1 Task 1.5: RAG 分块优化（300/80）
- Phase 1 Task 1.6: RAG query 改写（LLM 扩展关键词 + 混合检索 + 阈值 0.3）
- Phase 1 Task 1.7: RAG reindex 端点（POST /api/rag/reindex）
- Phase 1 Task 1.8: 对话记忆改进（增量摘要持久化到 chat_sessions.summary）
- Phase 2 Task 2.1: GuestPreference 模型
- Phase 2 Task 2.2: guest_preferences 建表迁移 + chat_sessions.summary 迁移
- Phase 2 Task 2.3: 偏好 CRUD API（GET/POST/DELETE /api/ai/preferences）
- Phase 2 Task 2.4: save_preference_tool（LLM 判断意图，不自动保存）
- Phase 2 Task 2.5: 偏好注入 prompt（chat_node + action_node）
- Phase 3 Task 3.1: complaint.py（关键词触发 + LLM 二次确认）
- Phase 3 Task 3.2: complaint_response 节点（WS + 工单 + 安抚 + 日志）
- Phase 3 Task 3.3: ComplaintAlert.tsx + AppLayout 集成

**Verification**:
- py_compile passes on all 11 backend files ✅
- tsc --noEmit passes on frontend ✅
- npm run build has pre-existing errors (CheckInModal, WorkOrderBoard, AIAuditPage) — not related to F017

**Blockers**: None
**Encoding note**: PowerShell @' '@ heredocs corrupt Chinese quotation marks ""→"". Used Python fixer scripts to patch. Future sessions should write Python files via Python scripts, not PowerShell heredocs.

**Next session picks up at**: Install google-search-results + configure SERPAPI_KEY + manual test web search

---

## F018: C ? AI ???? (2026-06-04)

**Goal**: ????????????????????? SerpAPI ????
**What was done**:
- config.py: added SERPAPI_KEY setting
- pyproject.toml: added google-search-results dependency
- Created web_search.py: search_web() + web_search_node()
- tools.py: classify_intent() added web_search category (4th intent)
- graph.py: added web_search_response node + routing

**Pending**:
- pip install google-search-results (network timeout, user needs to run manually)
- Configure SERPAPI_KEY in backend/.env
- Manual test: "??????" should return weather info

---

## Bug Fix: C 端发票预登记页面打不开 (2026-06-04)

**问题**: my_page.dart 导航到 /bill-detail 没传 orderId，且 app.dart 未注册该路由
**修复**:
- app.dart: import BillDetailPage + 新增 GoRoute /bill-detail/:orderId（ShellRoute 外，全屏无底部导航）
- my_page.dart: 菜单「我的账单」改为带 orderId 跳转，无订单时 SnackBar 提示
**验证**: flutter analyze 无新增 error/warning

---

## Bug Fix: C 端发票预登记页面打不开 (2026-06-04)

**问题**: my_page.dart 导航到 /bill-detail 没传 orderId，且 app.dart 未注册该路由
**修复**:
- app.dart: import BillDetailPage + 新增 GoRoute /bill-detail/:orderId（ShellRoute 外，全屏无底部导航）
- my_page.dart: 菜单「我的账单」改为带 orderId 跳转，无订单时 SnackBar 提示
**验证**: flutter analyze 无新增 error/warning