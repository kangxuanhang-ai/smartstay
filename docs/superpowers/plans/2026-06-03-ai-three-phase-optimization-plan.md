# AI 智能体三阶段优化实施计划
> **For agentic workers:** 使用 superpowers:executing-plans 逐 task 实施。Steps 使用 checkbox (`- [ ]`) 跟踪进度。

**Goal:** 三阶段优化 SmartStay AI：质量提升 → 偏好记忆 → 投诉自动响应
**Architecture:** 后端 AI 模块优化，SSE 协议不变，C 端无需改动
**Tech Stack:** LangGraph, DeepSeek Chat, fastembed, pgvector, SQLAlchemy, FastAPI

---

## 文件结构

### 新建文件
- `backend/app/models/preference.py` — GuestPreference 模型
- `backend/app/ai/complaint.py` — 投诉检测 + 处理
- `frontend/src/components/ComplaintAlert.tsx` — B 端投诉通知组件

### 修改文件
| 文件 | Phase | 改动说明 |
|------|-------|---------|
| `backend/app/ai/graph.py` | 1+2+3 | Prompt 重写、偏好注入、投诉节点 |
| `backend/app/ai/tools.py` | 1+2 | classify_intent 改进、save_preference_tool |
| `backend/app/ai/rag.py` | 1 | 分块优化、query 改写、阈值提升 |
| `backend/app/ai/state.py` | 2 | 新增 preferences 字段 |
| `backend/app/api/ai.py` | 1+2 | 对话摘要、偏好 API、偏好加载 |
| `backend/app/api/rag.py` | 1 | 新增 reindex 端点 |
| `backend/app/core/database.py` | 2 | guest_preferences 建表 |
| `frontend/src/hooks/useWebSocket.ts` | 3 | complaint.alert 事件 |

---

## Phase 1：智能体质量提升

### Task 1.1: chat_node Prompt 重写
**文件:** `backend/app/ai/graph.py` — `chat_node` 函数

**改动:**
1. 从 state 读取 room_id，查询住客姓名（通过 async_session 查 orders + guests）
2. 获取当前 CST 时间
3. 构造结构化 system prompt，包含：
   - 角色设定："你是小智，智宿云酒店的 AI 虚拟管家"
   - 回复规范：简短回复用纯文本；信息量大的回复允许加粗和列表，禁用标题和代码块
   - 上下文：当前时间、房间号、住客姓名
   - 3 条 few-shot 示例
4. 保留 recent = state["messages"][-10:] 逻辑

**验证:** py_compile 通过

---

### Task 1.2: action_node Prompt 重写
**文件:** `backend/app/ai/graph.py` — `action_node` 函数

**改动:**
1. 将当前 system_msg 拆分为结构化段落：
   - 角色：一句话
   - 可用工具：工具名 + 一句话描述（去掉冗长参数表）
   - 参数规则：精简设备参数表为紧凑格式
   - 核心约束：room_id 系统注入、多请求返回多 tool_calls
   - 2 个 few-shot 示例
2. 保留 MAX_ITERATIONS=5 循环逻辑不变
3. 保留关键词兜底逻辑不变

**验证:** py_compile 通过

---

### Task 1.3: knowledge_node Prompt 重写
**文件:** `backend/app/ai/graph.py` — `knowledge_node` 函数

**改动:**
1. 在 system_prompt 中添加：
   - "如果知识库信息不完整或无匹配，诚实告知住客并建议联系前台"
   - "绝对不要编造知识库中没有的信息"
2. 注入住客上下文（房间号）

**验证:** py_compile 通过

---

### Task 1.4: classify_intent 改进
**文件:** `backend/app/ai/tools.py` — `classify_intent` 函数

**改动:**
1. 在 prompt 中添加 8 条 few-shot 示例：
   - "你好" → chat
   - "谢谢" → chat
   - "空调好像坏了" → action
   - "帮我开灯" → action
   - "健身房几点开门" → knowledge
   - "延迟退房怎么办" → knowledge
   - "可以延迟退房吗" → knowledge
   - "送瓶水过来" → action
2. 添加明确规则："询问政策/规则/流程 → knowledge，不是 action"
3. 保持关键词兜底不变

**验证:** py_compile 通过

---

### Task 1.5: RAG 分块优化
**文件:** `backend/app/ai/rag.py` — `process_and_store` 函数

**改动:**
1. chunk_size: 500 → 300
2. chunk_overlap: 50 → 80

**验证:** py_compile 通过

---

### Task 1.6: RAG Query 改写
**文件:** `backend/app/ai/rag.py`

**改动:**
1. 新增 `async def rewrite_query(user_input: str) -> list[str]`
   - 使用 LLM (deepseek-chat, temperature=0) 将用户输入改写为 2-3 个搜索关键词
   - prompt: "将以下用户问题改写为 2-3 个适合知识库搜索的关键词，每行一个。只输出关键词，不要解释。"
   - 如果 LLM 失败，fallback 返回 [user_input]
2. 修改 `query_vector_store`:
   - 调用 rewrite_query 获取关键词列表
   - 对每个关键词分别做向量搜索，合并结果
   - 按 content 去重，取 top-k
   - 相似度阈值从 0.05 提升到 0.3
   - 保留 LIKE 关键词兜底

**验证:** py_compile 通过

---

### Task 1.7: RAG Reindex 端点
**文件:** `backend/app/ai/rag.py` + `backend/app/api/rag.py`

**改动:**
1. 在 `rag.py` 中新增 `async def reindex_all()`:
   - 查询所有 rag_documents
   - 删除所有 rag_embeddings
   - 用新的 chunk_size=300, overlap=80 重新处理每个文档
2. 在 `api/rag.py` 中新增 `POST /api/rag/reindex` 端点:
   - 仅 admin 角色可调用
   - 调用 reindex_all()
   - 返回处理结果

**验证:** py_compile 通过

---

### Task 1.8: 对话记忆改进
**文件:** `backend/app/api/ai.py` + `backend/app/core/database.py` + `backend/app/models/chat.py`

**改动:**
1. `chat.py` ChatSession 模型新增字段：`summary: Optional[str] = Field(default=None)`
2. `database.py` init_db 添加迁移：`ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS summary TEXT`
3. `api/ai.py` ai_chat 函数：
   - 加载历史消息后，判断总数是否 > 20
   - 如果 > 20：
     - 检查 session.summary 是否已有摘要
     - 如果无摘要：将第 1~(N-10) 条消息用 LLM 压缩为摘要（≤100字），存入 session.summary
     - 如果有摘要且有新消息（摘要之后产生的）：将新消息增量追加到摘要中
     - 保留最近 10 条消息 + 摘要作为 system message 插入消息列表开头
   - 如果 ≤ 20：保持现有逻辑不变

**优势:** 摘要持久化到数据库，避免每次请求都重新调 LLM 做摘要；增量更新只处理新增部分。

**验证:** py_compile 通过

---

### Task 1.9: Phase 1 验证
**验证步骤:**
1. `cd backend && poetry run python -m py_compile app/main.py`
2. 手动测试意图分类准确性
3. 手动测试 RAG 检索质量
4. 发送 >20 条消息测试对话摘要

---

## Phase 2：长期记忆 — 住客偏好设置

### Task 2.1: GuestPreference 模型
**文件:** 新建 `backend/app/models/preference.py`

**内容:**
```python
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel
from app.core.utils import cst_now

class GuestPreference(SQLModel, table=True):
    __tablename__ = "guest_preferences"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    guest_id: uuid.UUID = Field(foreign_key="guests.id", index=True)
    key: str = Field(max_length=50)  # ac_temp, curtain, bedside_light, bedroom_light, living_light, ac_mode
    value: str = Field(max_length=20)
    updated_at: datetime = Field(default_factory=cst_now)
```

**验证:** py_compile 通过

---

### Task 2.2: 数据库迁移
**文件:** `backend/app/core/database.py` — `init_db` 函数

**改动:**
在现有迁移块之后添加：
```python
try:
    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS guest_preferences (
            id UUID PRIMARY KEY,
            guest_id UUID NOT NULL REFERENCES guests(id),
            key VARCHAR(50) NOT NULL,
            value VARCHAR(20) NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(guest_id, key)
        )
    """))
except Exception:
    pass
```

**验证:** py_compile 通过

---

### Task 2.3: 偏好 API 端点
**文件:** `backend/app/api/ai.py`

**新增 3 个端点:**

1. `GET /api/ai/preferences`
   - 依赖 get_current_user (Guest)
   - 查询 guest_preferences WHERE guest_id = current_user.id
   - 返回 dict: {key: value, ...}

2. `POST /api/ai/preferences`
   - Body: {"key": "ac_temp", "value": "24"}
   - UPSERT: 如果 (guest_id, key) 已存在则更新 value，否则插入
   - 返回 {"ok": true}

3. `DELETE /api/ai/preferences/{key}`
   - 删除指定偏好
   - 返回 {"ok": true}

**验证:** py_compile 通过

---

### Task 2.4: AI 工具 — save_preference_tool
**文件:** `backend/app/ai/tools.py`

**改动:**
1. 新增工具函数：
```python
@tool
async def save_preference_tool(key: str, value: str, guest_id: str = "") -> str:
    """保存住客的环境偏好设置。
    key: ac_temp / curtain / bedside_light / bedroom_light / living_light / ac_mode
    value: 对应值，如 "24", "80", "true", "cool"
    guest_id: 由系统自动注入
    """
```
2. 在 build_tools() 中注册
3. **不自动保存**：control_device_tool 不触发偏好保存。偏好保存由 AI 通过对话判断：
   - 住客明确表达偏好时（"我喜欢 25 度"、"以后都调到 25 度"、"默认设为…"）→ AI 调用 save_preference_tool
   - 住客只是临时操作（"调到 20 度"、"把灯关了"）→ AI 只执行设备控制，不保存偏好
   - 判断逻辑在 action_node 的 system prompt 中说明，让 LLM 决定是否调用 save_preference_tool

**验证:** py_compile 通过

---

### Task 2.5: 偏好注入 Prompt
**文件:** `backend/app/ai/state.py` + `backend/app/ai/graph.py` + `backend/app/api/ai.py`

**改动:**
1. state.py: AgentState 新增 `preferences: Optional[dict] = None`
2. api/ai.py: ai_chat 端点中查询 guest_preferences，注入 initial_state["preferences"]
3. graph.py chat_node: 
   - 如果有偏好：在 prompt 中添加 "住客偏好：空调 24°C，窗帘 80%..."
   - 如果无偏好且首次聊天：添加 "主动询问住客的环境偏好（温度、灯光、窗帘）"
4. graph.py action_node: 在 prompt 中添加：
   - "如果住客说'跟上次一样'，直接应用偏好值"
   - "只在住客明确表达长期偏好时（如'我喜欢/以后都/默认设为'）才调用 save_preference_tool，临时操作不保存"

**验证:** py_compile 通过

---

### Task 2.6: Phase 2 验证
**验证步骤:**
1. py_compile 通过
2. 测试偏好 CRUD API
3. 测试 AI 聊天中的偏好读取和保存
4. 测试临时操作（"调到 20 度"）不触发偏好保存
5. 测试明确偏好（"我喜欢 25 度"）触发偏好保存

---

## Phase 3：主动式 Agent — 投诉自动响应

### Task 3.1: 投诉检测模块
**文件:** 新建 `backend/app/ai/complaint.py`

**内容:**
```python
COMPLAINT_KEYWORDS = [
    "投诉", "不满", "差评", "太差", "垃圾", "恶心", "退款", "换房",
    "受不了", "忍不了", "态度差", "服务差", "不干净", "有虫", "漏水",
    "没热水", "太吵", "隔音差", "骗人", "坑人", "报警", "消协", "12315",
]

async def detect_complaint(user_input: str, llm) -> dict:
    """检测是否为投诉/不满。
    关键词只作为"疑似"触发器，必须经 LLM 二次确认才判定为投诉：
    1. 关键词匹配 → 命中则标记 suspicious=True，交给 LLM 确认
    2. 未命中关键词 → 也交给 LLM 做情感分析（兜底，防止关键词遗漏）
    3. 只有 LLM 确认为投诉才返回 is_complaint=True
    """
```

关键词匹配逻辑：
- 命中关键词 → `suspicious=True`，但不直接判定为投诉
- 未命中 → `suspicious=False`

LLM 二次确认 prompt（无论是否命中关键词都走这一步）：
```
你是一个酒店 AI 情感分析器。判断以下住客消息是否表达真实的不满、投诉或强烈负面情绪。
注意区分：
- 报修/求助（"空调不太好用"）→ 不是投诉，是正常服务请求
- 闲聊评价（"房间有点小"）→ 不是投诉，是闲聊
- 真正的投诉/不满（"服务太差了"、"我要投诉"、"受不了了"）→ 是投诉
- 如果 suspicious=true，说明消息中包含投诉相关词汇，请仔细判断语境

suspicious: {suspicious}
消息：{user_input}

只输出 JSON：{"is_complaint": true/false, "severity": "low/medium/high", "summary": "一句话总结"}
```

**验证:** py_compile 通过

---

### Task 3.2: 投诉处理节点
**文件:** `backend/app/ai/graph.py`

**改动:**
1. 新增 `complaint_response` 节点函数：
   - 生成安抚回复（LLM: "住客表达了不满。请生成简短真诚的回复：道歉 + 告知已通知前台 + 承诺尽快解决"）
   - 通知前台：WebSocket broadcast_biz {"event": "complaint.alert", "data": {...}}
   - 创建紧急工单：work_orders type="complaint", status="submitted", ai_generated=True
   - 记录日志：ai_security_logs violation_type="complaint"
   - 返回 state，business_cards 包含投诉处理卡片

2. 修改 route_by_intent：
   - 先调用 detect_complaint
   - 如果是投诉 → "complaint"
   - 否则走原有 classify_intent 逻辑

3. 修改 build_graph：
   - 新增 "complaint_response" 节点
   - 路由表添加 "complaint": "complaint_response"
   - complaint_response → END

**验证:** py_compile 通过

---

### Task 3.3: B 端投诉通知
**文件:** `frontend/src/hooks/useWebSocket.ts` + 新建 `frontend/src/components/ComplaintAlert.tsx`

**改动:**
1. useWebSocket.ts: 新增 complaint.alert 事件类型定义
2. ComplaintAlert.tsx:
   - 使用 Ant Design notification.error 显示投诉通知
   - 包含房间号、严重程度、摘要
   - 点击可跳转到工单页面
3. 在 AppLayout.tsx 中集成 ComplaintAlert 组件

**验证:** tsc --noEmit 通过, npm run build 通过

---

### Task 3.4: Phase 3 验证
**验证步骤:**
1. py_compile + tsc --noEmit 通过
2. 发送 "你们服务太差了，我要投诉" → 检测为投诉
3. WebSocket 收到 complaint.alert 事件
4. 工单表新增 complaint 类型工单
5. AI 回复包含道歉和"已通知前台"
6. 发送 "今天天气不错" → 不触发投诉检测

---

## 假设与默认值

1. LLM: 继续使用 DeepSeek Chat (deepseek-chat)
2. 嵌入: 继续使用 bge-small-zh-v1.5 (512d)
3. 偏好: 简单 key-value，6 个 key（ac_temp, curtain, bedside_light, bedroom_light, living_light, ac_mode）
4. 投诉检测: 关键词作为疑似触发器 + LLM 二次确认（降低误判率）
5. Reindex: 管理员手动触发
6. 对话摘要: 消息 >20 条时触发，摘要 ≤100 字
7. 偏好询问: 仅首次聊天且无偏好时主动询问
8. 工单: 复用 work_orders 表，type 新增 "complaint"
9. C 端: 不受影响
