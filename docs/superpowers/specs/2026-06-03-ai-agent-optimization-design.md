# AI Agent 高级优化设计

**日期**：2026-06-03
**范围**：后端 `backend/app/ai/` 模块（graph.py, tools.py, guard.py, state.py）
**分 3 期实施**：代码质量优化 → 多步 agent 循环 → 对话记忆
**C 端不受影响**：SSE 协议不变，Flutter 无需改动

---

## 现状分析

### 当前架构
```
START → process_input(空) → [route_by_intent] → chat/knowledge/action → END
```
- `process_input_node`：空函数，直接透传
- `classify_node`：死代码，注册了但从未被路由到
- `action_node`：LLM 调一次工具就结束，串行执行 tool_calls
- 所有 LLM 调用只传最后一条用户消息，无对话记忆

### 已发现问题
| # | 问题 | 影响 |
|---|------|------|
| 1 | `classify_node` 是死代码 | 代码清洁度 |
| 2 | `process_input_node` 是空函数 | 代码清洁度 |
| 3 | 工具调用串行执行 | 性能 |
| 4 | WS 广播代码重复（主路径+兜底） | 代码质量 |
| 5 | 意图分类关键词太宽泛（"帮我"匹配所有） | 分类准确度 |
| 6 | LLM 不带历史消息 | 对话连贯性 |
| 7 | modify_room_price_tool 是 stub | 功能完整性 |

---

## 期 1：代码质量优化

### 1.1 清理死代码
- 删除 `classify_node` 和 `process_input_node`
- `route_by_intent` 直接从 `START` 出发

### 1.2 并行工具调用
- `_execute_single_tool` 抽取为独立函数
- `asyncio.gather` 并行执行

### 1.3 去重 WebSocket 广播
- `_broadcast_work_order` 公共函数

### 1.4 改善意图分类
- 强关键词直接命中，弱关键词需搭配操作词

---

## 期 2：多步 Agent 循环

action_node 改为循环：LLM 调工具 → 结果喂回 → 再调，MAX_ITERATIONS=5。

---

## 期 3：对话记忆

LLM 调用带最近 10 条历史消息。
