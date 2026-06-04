# AI 智能体三阶段优化设计

**日期**：2026-06-03
**范围**：后端 `backend/app/ai/` 模块、相关 API/模型、B 端 WebSocket 通知
**分 3 期实施**：智能体质量提升 → 长期记忆（偏好设置） → 主动式 Agent（投诉自动响应）
**C 端不受影响**：SSE 协议不变，Flutter 无需改动

---

## 现状分析

### 当前 AI 架构
```
START → [route_by_intent] → chat/knowledge/action → END
```
- `route_by_intent`：关键词兜底 + LLM 意图分类
- `chat_node`：闲聊，prompt 极简（一句话角色设定）
- `knowledge_node`：RAG 检索 + LLM 回答
- `action_node`：工具调用，MAX_ITERATIONS=5 循环

### 已发现问题
| # | 问题 | 影响 |
|---|------|------|
| 1 | chat_node prompt 太简单，无角色人格、无回复规范 | 回答质量不稳定 |
| 2 | action_node prompt 是"墙式文本"，设备参数表冗长 | LLM 容易迷失，工具调用准确率下降 |
| 3 | knowledge_node 无"信息不完整"处理指令 | 编造信息风险 |
| 4 | classify_intent few-shot 示例不足，边界 case 频繁错分 | "延迟退房怎么办" 被分为 action |
| 5 | RAG chunk_size=500 太粗，threshold=0.05 太低 | 检索噪音大，低质量匹配多 |
| 6 | 无 query 改写，用户口语化输入直接做 embedding | "空调好像坏了" 命中率低 |
| 7 | 对话历史加载 20 条无摘要，长对话 token 浪费 | 上下文窗口被低价值消息占用 |
| 8 | 无住客偏好记忆，每次入住从零开始 | 体验不连贯 |
| 9 | 无投诉检测，住客不满时无主动响应 | 服务升级机会丢失 |

---

## Phase 1：智能体质量提升

### 1.1 Prompt 工程重写
**改动文件：** `graph.py`, `tools.py`

**chat_node prompt：**
- 角色人格："小智"，智宿云酒店 AI 虚拟管家
- 回复规范：简短操作回复用纯文本；信息量较大的回复（知识库结果、设施介绍、政策说明）允许适度使用 markdown（加粗关键词、无序列表），但不要用标题和代码块
- 上下文注入：当前时间、房间号、住客姓名
- 3 条 few-shot 示例

**action_node prompt：**
- 拆分为结构化段落：角色 → 工具 → 参数规则 → 约束 → 示例
- 精简设备参数表
- 2 个 few-shot 示例（单工具 + 多工具并行）

**knowledge_node prompt：**
- 添加"信息不完整时诚实告知"指令
- 添加"不要编造信息"约束

**classify_intent：**
- 8 条 few-shot 示例覆盖边界 case
- 明确"政策类问题 → knowledge"规则

### 1.2 RAG 检索优化
**改动文件：** `rag.py`, `api/rag.py`

- chunk_size: 500 → 300，chunk_overlap: 50 → 80
- 新增 `rewrite_query()`：LLM 将用户输入改写为 2-3 个搜索关键词
- 相似度阈值：0.05 → 0.3
- 混合检索：多关键词向量搜索 + LIKE 兜底
- 新增 `reindex_all()` + `POST /api/rag/reindex` 端点

### 1.3 对话记忆改进
**改动文件：** `api/ai.py`

- 消息 >20 条时：保留最近 10 条 + LLM 摘要旧消息
- 摘要注入 system prompt

---

## Phase 2：长期记忆 — 住客偏好设置

### 2.1 数据模型
**新建：** `models/preference.py`

`guest_preferences` 表：id, guest_id (FK), key, value, updated_at
唯一约束：(guest_id, key)

### 2.2 API 端点
**改动文件：** `api/ai.py`

- `GET /api/ai/preferences`
- `POST /api/ai/preferences`
- `DELETE /api/ai/preferences/{key}`

### 2.3 AI 工具集成
**改动文件：** `tools.py`, `graph.py`, `state.py`

- 新增 `save_preference_tool`（AI 判断住客意图后决定是否调用）
- **不自动保存**：临时操作不保存，只有住客明确表达偏好（"我喜欢/以后都/默认设为"）时才保存
- 偏好注入 system prompt
- AI 主动询问新住客的环境偏好

---

## Phase 3：主动式 Agent — 投诉自动响应

### 3.1 投诉检测
**新建：** `ai/complaint.py`

关键词作为"疑似投诉"触发器 + LLM 二次确认（降低误判率）
关键词命中不直接判定投诉，必须经 LLM 确认后才走投诉流程
返回：is_complaint, severity (low/medium/high), summary

### 3.2 投诉处理
**改动文件：** `graph.py`

新增 `complaint_response` 节点：
1. WebSocket `complaint.alert` 通知前台
2. 创建紧急工单（type=complaint）
3. LLM 生成安抚回复
4. 记录 ai_security_logs

### 3.3 B 端通知
**改动文件：** `useWebSocket.ts`, 新建 `ComplaintAlert.tsx`

- 订阅 `complaint.alert` 事件
- 弹出醒目通知（Ant Design notification.error）
