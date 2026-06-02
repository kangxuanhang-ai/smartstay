# C 端 AI 聊天增强设计

**日期**：2026-06-02
**范围**：C 端 Flutter AI 聊天页面 + 后端少量新增接口
**分 3 期实施**：UX 体验优化 → 功能增强 → 代码重构

---

## 现状分析

### 当前功能
- 基本文字聊天 + SSE 流式输出
- 业务卡片（成功/失败状态，仅显示 emoji + 标题）
- 401 自动 token 刷新
- 双平台支持（Web 用 dart:html，Native 用 http 包）
- 未登录用户看到 AuthPrompt 遮罩

### 已发现问题
| 类别 | 问题 |
|------|------|
| UX | 流式输出时无法取消 |
| UX | AI 思考时（第一个 token 前）无任何视觉反馈 |
| UX | 工具执行中用户看不到中间状态 |
| UX | 麦克风按钮存在但未实现 |
| UX | 没有快捷提问入口 |
| 功能 | AI 响应不支持 Markdown 渲染 |
| 功能 | 业务卡片不可交互 |
| 功能 | 无多会话历史 |
| 代码 | `_sendViaWeb` 和 `_sendViaDio` 有 ~80 行重复 SSE 解析逻辑 |
| 代码 | `ChatMessage.cards` 是无类型 `List<Map<String, dynamic>>` |

---

## 期 1：UX 体验优化

纯 C 端改动，不涉及后端。

### 1.1 停止/取消按钮

**行为**：
- 流式输出时，发送按钮变为停止按钮（红色方块图标）
- 点击后取消 HTTP 请求（`_httpSub?.cancel()` / `_webRequest?.abort()`）
- 保持已收到的文本，`isStreaming` 设为 `false`
- 恢复发送按钮

**实现要点**：
- AIChatPage 输入栏根据 `state.isStreaming` 切换按钮图标和 onTap
- ChatBloc 需暴露 cancel 方法或在事件中处理
- 新增 `ChatStreamCancelled` 事件

### 1.2 打字指示器

**行为**：
- 发送消息后、收到第一个 `text` token 前，AI 气泡显示三点跳动动画
- 收到第一个 token 后替换为实际文本

**实现要点**：
- `ChatMessage` 增加 `isThinking` 字段（默认 `false`）
- `_onSend` 创建初始 AI 消息时设 `isThinking: true`
- 收到第一个 `type: "text"` 事件时设 `isThinking: false`
- UI 层：`isThinking == true` 时渲染 `_TypingIndicator` widget（三个点脉冲动画）

### 1.3 工具调用状态展示

**行为**：
- 后端执行工具时发送 `{"type": "card", ...}` 事件
- 收到 card 事件时，如果整体流仍在进行中（`isStreaming == true`），该卡片显示为"执行中"状态：progress indicator + card.title
- 当收到 `{"type": "done"}` 事件后（`isStreaming` 变为 `false`），所有卡片切换为最终状态：emoji + 标题
- 具体规则：`isStreaming == true` 时卡片显示加载动画；`isStreaming == false` 时显示最终结果

**实现要点**：
- 卡片组件从 `ChatBloc.state.isStreaming` 读取流状态
- `isStreaming` 为 true 时：显示 `CircularProgressIndicator`（小号）+ card.title
- `isStreaming` 为 false 时：显示 emoji（✅/❌）+ card.title

### 1.4 快捷提问标签

**行为**：
- 空聊天状态下方显示 3-4 个建议标签
- 点击标签等同于发送该文本
- 发送后标签消失（被聊天内容替代）
- AI 回复完成后，如果回复包含卡片（如工单创建成功），可在卡片下方显示相关后续建议（如 "查看工单状态"）

**动态逻辑**：
- 未登录：通用问题（"酒店有什么设施？"、"怎么预订房间？"、"酒店在哪里？"）
- 已入住：场景化（"空调太冷了"、"帮我打扫房间"、"附近有什么好吃的？"、"我想延迟退房"）
- 已退房：查询类（"查看我的账单"、"怎么开发票？"）

**实现要点**：
- 读取 `AuthBloc.state` 判断登录状态
- 读取 `RoomBloc.state` 判断是否入住
- 在输入栏上方用 `Wrap` 渲染标签
- 标签样式：圆角 chip，蓝色描边背景

---

## 期 2：功能增强

### 2.1 Markdown 渲染

**行为**：AI 回复中的加粗、列表、链接、代码块等正确渲染。

**实现要点**：
- 添加 `flutter_markdown` + `url_launcher` 依赖
- AI 消息的 `Text` 替换为 `MarkdownBody`
- 配置深色主题样式（文字色 `#c0c0e0`，链接色 `#60a5fa`，代码块背景 `_card`）
- 用户消息保持纯文本
- 链接点击用 `url_launcher` 打开

### 2.2 可交互业务卡片

**行为**：
- **工单卡片**：显示工单类型 + 状态，点击跳转 `/work-orders`
- **设备控制卡片**：显示设备名 + 操作结果 + 图标（空调/灯光/窗帘）
- **价格卡片**：显示房型 + 新价格
- **错误卡片**：红色边框 + 错误原因

**实现要点**：
- 后端 card JSON 的 `type` 字段决定渲染样式
- 定义 `_WorkOrderCard`、`_DeviceCard`、`_PricingCard`、`_ErrorCard` widget
- 用 `GestureDetector` 包裹，`onTap` 时通过 `context.go()` 跳转

### 2.3 语音输入

**行为**：
- 点击麦克风按钮 → 录音（按钮变红 + 脉冲动画）
- 再次点击停止 → 调用 STT API → 识别文字自动发送

**后端新增接口**：
```
POST /api/ai/transcribe
Content-Type: multipart/form-data
Body: audio file (m4a/wav)
Response: { "text": "识别出的文字" }
```

使用阿里云 ASR（智能语音交互）实现转写，与现有人脸识别共用阿里云账号。

**C 端实现要点**：
- 添加 `record`（录音）+ `permission_handler`（权限）依赖
- 录音格式：m4a（体积小、兼容性好）
- 录音状态管理：在 ChatState 中增加 `isRecording` 字段
- 权限处理：首次使用时请求麦克风权限，拒绝后显示提示

### 2.4 多会话历史

**行为**：
- AI 聊天 header 右侧增加「历史」按钮（时钟图标）
- 点击显示会话列表（底部弹出面板或新页面）
- 列表项显示：时间 + 首条消息摘要（截取前 30 字）
- 点击历史会话加载完整聊天记录
- 支持新建会话（清空当前对话）

**后端新增接口**：
```
GET /api/ai/chat/sessions
Response: [{ "id": "...", "created_at": "...", "first_message": "...", "status": "active" }]
```

查询当前住客的所有 ChatSession，按创建时间倒序。

**C 端实现要点**：
- ChatBloc 增加 `ChatSessionLoadRequested` 和 `ChatNewSessionRequested` 事件
- ChatState 增加 `sessions` 列表和 `currentSessionId`
- 会话切换时：清空 messages → 加载历史消息 → 更新 currentSessionId
- 新建会话时：清空 messages → currentSessionId = null → 下次发送自动创建新 session

---

## 期 3：代码重构

纯内部重构，不改变用户可见行为。

### 3.1 抽取公共 SSE 解析逻辑

**问题**：`_sendViaWeb` 和 `_sendViaDio` 各有 ~80 行相同的 SSE 行解析代码。

**方案**：创建 `SSEStreamHandler` 类：
- 输入：原始字符串 chunk
- 输出：`Stream<SSEEvent>`（复用现有 SSEEvent 类）
- 封装行分割、`data:` 前缀检查、JSON 解析、type 分发
- Web 路径：`onProgress` 中把增量文本喂给 handler
- Native 路径：`stream.transform(Utf8Decoder())` 输出喂给 handler
- `ChatBloc._sendViaWeb` 和 `_sendViaDio` 各缩减到 ~30 行

### 3.2 类型安全的卡片模型

**问题**：`ChatMessage.cards` 是 `List<Map<String, dynamic>>`，无编译时检查。

**方案**：
```dart
enum ChatCardType { success, error, deviceControl, workOrder, pricing, info }

class ChatCard {
  final ChatCardType type;
  final String title;
  final String? subtitle;
  final Map<String, dynamic>? metadata;

  const ChatCard({required this.type, required this.title, this.subtitle, this.metadata});

  factory ChatCard.fromJson(Map<String, dynamic> json) {
    return ChatCard(
      type: ChatCardType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => ChatCardType.info,
      ),
      title: json['title'] ?? '',
      subtitle: json['subtitle'],
      metadata: json,
    );
  }
}
```

替换所有 `Map<String, dynamic>` 为 `ChatCard`。

### 3.3 ChatBloc 拆分

**问题**：ChatBloc 职责过多（消息管理 + SSE 流 + token 刷新 + 平台分支）。

**方案**：抽取 `ChatStreamService`：
- 负责 HTTP 请求建立、SSE 解析、token 刷新重试
- 暴露 `Stream<ChatStreamEvent>`（text/card/done/error 事件）
- ChatBloc 只负责：接收事件 → 更新 state
- `_sendViaWeb` 和 `_sendViaDio` 移入 service，ChatBloc 通过统一接口调用

---

## 后端改动汇总

| 接口 | 方法 | 期数 | 用途 |
|------|------|------|------|
| `/api/ai/transcribe` | POST | 期 2 | 语音转文字（接收音频文件，调用 STT） |
| `/api/ai/chat/sessions` | GET | 期 2 | 列出当前住客的所有会话 |

现有 `/api/ai/chat` 和 `/api/ai/chat/{session_id}/history` 无需修改。

---

## 依赖变更

### 期 2 新增 Flutter 依赖
- `flutter_markdown` — Markdown 渲染
- `url_launcher` — 链接点击打开
- `record` — 音频录制
- `permission_handler` — 权限请求

### 期 2 新增后端依赖
- 无（DeepSeek API 已有，STT 通过其 Whisper 接口调用）

---

## 文件变更预估

### 期 1（~6 个文件）
- `blocs/chat/chat_bloc.dart` — 新增 cancel 事件处理
- `blocs/chat/chat_event.dart` — 新增 `ChatStreamCancelled`
- `blocs/chat/chat_state.dart` — `ChatMessage` 增加 `isThinking`
- `pages/ai_chat/ai_chat_page.dart` — 停止按钮、打字指示器、快捷标签
- 新增 `widgets/typing_indicator.dart` — 三点跳动动画
- 新增 `widgets/quick_chips.dart` — 快捷提问标签

### 期 2（~8 个文件）
- `pages/ai_chat/ai_chat_page.dart` — Markdown 渲染、可交互卡片、语音按钮、历史入口
- `blocs/chat/chat_bloc.dart` — 语音录制、会话管理
- `blocs/chat/chat_event.dart` — 新增事件
- `blocs/chat/chat_state.dart` — 新增状态字段
- 新增 `widgets/chat_card.dart` — 可交互卡片组件
- 新增 `pages/ai_chat/session_list_page.dart` — 会话历史页面
- `backend/app/api/ai.py` — 新增 transcribe + sessions 接口
- `pubspec.yaml` — 新增依赖

### 期 3（~5 个文件）
- 新增 `core/sse_stream_handler.dart` — 公共 SSE 解析
- 新增 `models/chat_card.dart` — 类型安全卡片模型
- 新增 `services/chat_stream_service.dart` — 流处理服务
- `blocs/chat/chat_bloc.dart` — 重构为使用 service
- `blocs/chat/chat_state.dart` — 使用 ChatCard 类型
