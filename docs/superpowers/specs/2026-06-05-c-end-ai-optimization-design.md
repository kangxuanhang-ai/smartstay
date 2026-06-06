# C端 AI 功能优化与新增设计文档

> 日期：2026-06-05
> 范围：6 项现有功能优化 + 2 项新功能
> UI 风格：精致柔和（渐变、毛玻璃、圆角、柔和阴影）
> 动画：适度（卡片展开、涟漪、入场、转场）

---

## 一、设计系统

### 1.1 色彩体系

```dart
// 主色（渐变起止）
Color primaryStart = Color(0xFF667EEA);  // 紫蓝
Color primaryEnd   = Color(0xFF764BA2);  // 深紫

// 背景
Color bgDark   = Color(0xFF0F0F23);  // 页面深色背景
Color bgCard   = Color(0xFF1A1A2E);  // 卡片背景
Color bgInput  = Color(0xFF16213E);  // 输入框背景

// 功能色
Color success  = Color(0xFF10B981);  // 绿色（成功/设备控制）
Color warning  = Color(0xFFF59E0B);  // 琥珀色（工单）
Color error    = Color(0xFFEF4444);  // 红色（错误）
Color info     = Color(0xFF3B82F6);  // 蓝色（信息）
Color pricing  = Color(0xFF8B5CF6);  // 紫色（定价）

// 文字
Color textPrimary   = Color(0xFFFFFFFF);  // 白色主文字
Color textSecondary = Color(0xFF9CA3AF);  // 灰色次要文字
Color textTertiary  = Color(0xFF6B7280);  // 深灰辅助文字
```

### 1.2 圆角与阴影

```dart
// 圆角
Radius sm = Radius.circular(8);    // 小组件
Radius md = Radius.circular(12);   // 卡片
Radius lg = Radius.circular(16);   // 大面板
Radius full = Radius.circular(999); // 药丸形

// 阴影
BoxShadow soft = BoxShadow(
  color: Colors.black.withOpacity(0.15),
  blurRadius: 12,
  offset: Offset(0, 4),
);

BoxShadow glow = BoxShadow(
  color: primaryStart.withOpacity(0.3),
  blurRadius: 20,
  offset: Offset(0, 0),
);
```

### 1.3 毛玻璃效果

```dart
// 用于输入栏、顶部导航
BackdropFilter(
  filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
  child: Container(
    color: Colors.white.withOpacity(0.05),
    // ...
  ),
)
```

### 1.4 动画规范

| 类型 | 时长 | 曲线 |
|------|------|------|
| 页面转场 | 300ms | easeInOutCubic |
| 卡片展开/收起 | 250ms | easeOutBack |
| 按钮涟漪 | 200ms | easeOut |
| 列表项入场 | 300ms | easeOutCubic（带 50ms 间隔） |
| 输入框聚焦 | 200ms | easeOut |
| 语音波形 | 循环 | Linear |

---

## 二、功能 1：语音输入

### 2.1 后端

**现有接口确认：**
- `POST /api/ai/chat` 接收 `{"message": "...", "new_session": bool, "web_search": bool}`
- 后端已有 `backend/app/aliyun/asr.py` 实现阿里云语音识别

**需要新增：**
```
POST /api/ai/asr
请求：multipart/form-data，字段 file（音频文件）
响应：{"text": "识别出的文字"}
认证：Bearer token
```

实现逻辑：
1. 接收音频文件（AAC/PCM/WAV）
2. 调用 `backend/app/aliyun/asr.py` 的 ASR 函数
3. 返回识别文本
4. 音频文件不持久化，处理完即丢弃

### 2.2 Flutter 前端

**新建文件：** `smartstay-flutter/lib/core/voice_service.dart`

```dart
class VoiceService {
  // 单例
  static final VoiceService instance = VoiceService._();
  VoiceService._();

  // 录音状态
  bool isRecording = false;
  Timer? _durationTimer;
  int _durationSeconds = 0;

  // 开始录音 → 调用 record 包
  Future<void> startRecording() async {
    // 1. 检查权限（permission_handler）
    // 2. 使用 record 包开始录音（输出 AAC 格式）
    // 3. 启动计时器，每秒更新 duration
    // 4. 更新 UI 状态
  }

  // 停止录音 → 返回音频文件路径
  Future<String?> stopRecording() async {
    // 1. 停止 record
    // 2. 取消计时器
    // 3. 返回临时文件路径
  }

  // 上传到后端 ASR → 返回文字
  Future<String?> transcribe(String audioPath) async {
    // 1. 构建 multipart 请求
    // 2. POST /api/ai/asr
    // 3. 解析响应，返回 text
    // 4. 删除临时音频文件
  }

  // 取消录音
  Future<void> cancelRecording() async {
    // 停止 record，不上传
  }
}
```

**修改文件：** `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

UI 交互逻辑：
```
用户长按麦克风按钮
  → 显示录音中状态（波形动画 + 录音时长）
  → 松手 → 上传到 ASR
  → 显示"识别中..."加载态
  → 识别结果填入输入框
  → 用户可编辑后发送（或直接发送）
```

麦克风按钮状态：
1. **空闲态**：灰色麦克风图标，无事件
2. **录音中态**：红色麦克风 + 波形动画 + 时长显示（"0:03"）
3. **识别中态**：转圈 + "识别中..."
4. **识别完成态**：文字自动填入输入框，麦克风恢复空闲

波形动画实现：
```dart
// 用 AnimatedContainer 模拟波形
// 5-7 根竖条，高度随录音音量随机变化
// 使用 AnimationController + Timer 周期刷新
class VoiceWaveAnimation extends StatefulWidget {
  // 宽度 40px，高度 30px
  // 5 根竖条，宽 3px，间距 3px
  // 每 150ms 随机更新高度（6-24px）
  // 颜色：从 primaryStart 到 primaryEnd 渐变
}
```

**错误处理：**
- 无权限 → 弹出引导弹窗"请在系统设置中允许麦克风权限"
- 录音失败 → Toast 提示"录音失败，请重试"
- ASR 超时（>10s）→ 自动取消，提示"识别超时，请重试"
- ASR 返回空 → 提示"未识别到语音，请再试一次"
- 网络断开 → 提示"网络不可用，请检查网络连接"

### 2.3 修改 chat_card.dart

在现有 6 种卡片类型基础上，新增 `voice` 类型用于语音消息气泡。

---

## 三、功能 2：智能快捷短语

### 3.1 逻辑

现有逻辑：根据 3 种登录状态显示固定文案。

优化后逻辑：

```
输入：当前时间、入住状态、房间状态、对话历史
输出：4 个快捷短语
```

**动态生成规则：**

| 场景条件 | 生成的短语 |
|---------|-----------|
| 入住第一天 上午 | "酒店有什么设施？", "附近有什么好吃的？", "Wi-Fi密码是什么？", "退房时间是几点？" |
| 入住第一天 晚上 | "帮我开灯", "空调调到24度", "附近有什么好吃的？", "酒店有什么设施？" |
| 入住第二天+ 早晨 | "帮我打扫房间", "我想延迟退房", "附近有什么好吃的？", "查一下我的账单" |
| 入住第二天+ 晚上 | "空调调到24度", "帮我关窗帘", "我想延迟退房", "需要送水" |
| 退房日 | "我想延迟退房", "帮我叫车", "查一下我的账单", "怎么开发票？" |
| 对话中有"空调"历史 | "空调调到24度", "空调太冷了", "关闭空调" |
| 对话中有"工单"历史 | "报修进度怎么样？", "帮我叫维修" |

### 3.2 实现

**修改文件：** `smartstay-flutter/lib/widgets/quick_chips.dart`

```dart
class QuickChips extends StatelessWidget {
  final Room? currentRoom;      // 房间信息（含 status）
  final List<ChatMessage> history; // 对话历史
  final DateTime now;            // 当前时间

  // 核心方法：generateChips()
  List<String> _generateChips() {
    // 1. 获取时间段（morning/afternoon/evening/night）
    // 2. 获取入住天数
    // 3. 检查对话历史关键词
    // 4. 根据优先级选择 4 个短语
    // 5. 去重，保证不超过 4 个
  }
}
```

**优先级规则：**
1. 退房日相关（延迟退房、叫车、账单）优先级最高
2. 入住天数相关（打扫、设施）次之
3. 时间段相关（开灯、空调）第三
4. 历史关键词相关（如果对话中有空调相关历史，空调短语优先）
5. 兜底：酒店设施、Wi-Fi、附近美食

### 3.3 UI

快捷短语样式保持现有药丸形，但增加微妙的入场动画：
- 4 个短语依次入场，间隔 50ms
- 使用 `SlideTransition` + `FadeTransition`
- 从下方滑入 10px + 透明度 0→1

---

## 四、功能 3：ChatCard 富交互升级

### 4.1 后端变更

现有卡片发送格式：
```json
{"type": "card", "card": {"type": "success", "title": "✅ 卧室灯光已调节", "detail": "..."}}
```

升级后格式：
```json
{
  "type": "card",
  "card": {
    "type": "deviceControl",
    "title": "✅ 空调温度已调节",
    "detail": "已将空调温度调整为 24°C",
    "metadata": {
      "device": "ac_temp",
      "value": 24,
      "device_states": {"ac_temp": 24, "bedroom_light": true, ...}
    }
  }
}
```

**后端修改（`graph.py` 的 `_execute_single_tool`）：**

在返回 card 时，将工具执行结果的详细信息放入 `metadata`：
- `deviceControl`：device 名称、新值、当前所有设备状态
- `workOrder`：工单 ID、类型、状态、内容
- `pricing`：房型、原价、建议价
- `error`：错误类型、建议操作

### 4.2 Flutter 前端

**修改文件：** `smartstay-flutter/lib/widgets/chat_card.dart`

**deviceControl 卡片升级：**

```
┌─────────────────────────────────┐
│ 🟢 空调温度已调节                │
│ 已将空调温度调整为 24°C          │
│ ┌─────────────────────────────┐ │
│ │ [温度滑块] 16°C ←——●→ 30°C │ │
│ │ 当前: 24°C                  │ │
│ └─────────────────────────────┘ │
│                     查看房间控制 ›│
└─────────────────────────────────┘
```

- 显示温度滑块（只读展示，不可拖动 — 避免复杂交互）
- 滑块颜色从蓝（16°C）渐变到红（30°C）
- 底部保留"查看房间控制"导航链接

**workOrder 卡片升级：**

```
┌─────────────────────────────────┐
│ 📋 送物工单已创建                │
│ 需要两瓶矿泉水                   │
│ ┌─────────────────────────────┐ │
│ │ ●已提交 ─── ○处理中 ─── ○已完成 │ │
│ │ 工单号: wo_abc123            │ │
│ └─────────────────────────────┘ │
│                     查看工单详情 ›│
└─────────────────────────────────┘
```

- 显示 3 步进度条（已提交 → 处理中 → 已完成）
- 当前状态用实心圆 + 高亮颜色
- 未来状态用空心圆 + 灰色连线

**pricing 卡片升级：**

```
┌─────────────────────────────────┐
│ 💰 价格建议                      │
│ 大床房 定价建议                   │
│ ┌──────────┬──────────┐         │
│ │ 当前价格  │ AI建议价  │         │
│ │  ¥300    │  ¥350    │         │
│ │ ──────── │ ──────── │         │
│ │ ████████ │ ██████████│         │
│ └──────────┴──────────┘         │
│ 原因: 周末需求上升               │
└─────────────────────────────────┘
```

- 显示价格对比（当前 vs 建议）
- 用柱状图表示价格高低
- 显示触发原因

**success/error/info 卡片：**
- 保持现有样式，但增加微妙的渐变边框
- error 卡片增加"重试"按钮（点击重新发送最后一条消息）
- success 卡片增加"撤销"按钮（如果适用）

### 4.3 卡片入场动画

所有卡片新增入场动画：
```dart
// 使用 AnimatedSize + FadeTransition
// 卡片从高度 0 + 透明度 0 展开到完整高度 + 透明度 1
// 时长 250ms，easeOutBack 曲线
```

---

## 五、功能 4：AI 回复评价机制

### 5.1 后端

**新增数据表：** `ai_chat_feedback`

```python
class AIChatFeedback(SQLModel, table=True):
    __tablename__ = "ai_chat_feedback"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="chat_sessions.id")
    message_id: uuid.UUID = Field(foreign_key="chat_messages.id")
    guest_id: uuid.UUID = Field(foreign_key="guests.id")
    rating: str  # "thumbs_up" | "thumbs_down"
    reason: str | None  # 点踩原因
    created_at: datetime = Field(default_factory=cst_now)
```

**新增 API：**

```
POST /api/ai/feedback
请求：{"message_id": "xxx", "rating": "thumbs_up|thumbs_down", "reason": "不准确|没理解我的意思|信息过时|其他"}
响应：{"ok": true}
认证：Bearer token
```

**在 `models/__init__.py` 导入新模型。**

### 5.2 Flutter 前端

**修改文件：** `smartstay-flutter/lib/widgets/chat_card.dart`（在 AI 消息气泡底部添加）

```
AI 回复内容...
┌─────────────────────────────┐
│ 设备已控制                   │
└─────────────────────────────┘
👍  👎  ← 评价按钮（仅在非流式状态时显示）
```

**评价交互流程：**
1. 每条 AI 回复下方显示 👍/👎 按钮（默认半透明，hover 时高亮）
2. 点击 👎 → 弹出底部选择面板（4 个原因 + 取消）
3. 点击 👍 → 立即调用 API，按钮变为实心绿色 ✓
4. 已评价后按钮固定，不可修改
5. 评价数据通过 SSE `done` 事件后的新事件发送（`type: "feedback_ready", message_id: "xxx"`）

**点踩原因选择面板：**

```
┌─────────────────────────────────┐
│  为什么觉得这个回复不好？         │
│                                 │
│  ┌───────────────────────────┐  │
│  │  📝 回复不准确             │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  🤔 没理解我的意思         │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  📅 信息过时               │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │  💬 其他原因               │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │       取消                 │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

面板样式：
- 从底部滑入，带 200ms 动画
- 每个选项是圆角卡片，点击时有涟漪效果
- 选择后自动关闭面板，调用 API

### 5.3 SSE 事件扩展

在 `done` 事件后，发送：
```
data: {"type": "feedback_ready", "message_id": "xxx"}
```

Flutter 端解析此事件，将 `message_id` 附加到对应的 AI 消息上，用于评价 API 调用。

---

## 六、功能 5：对话气泡优化

### 6.1 时间戳显示

**每条消息下方显示时间：**
- 格式：`HH:mm`（如 "14:30"）
- 位置：消息气泡右下角（用户消息）/ 左下角（AI 消息）
- 样式：`fontSize: 10, color: textTertiary`
- 只在以下情况显示：
  1. 第一条消息
  2. 与上一条消息间隔 > 5 分钟
  3. 日期变化时显示完整日期

**实现：** 在 `ChatMessage` 模型中添加 `timestamp` 字段（`DateTime`），在 BLoC 添加消息时设置。

### 6.2 复制功能

**长按 AI 消息 → 显示复制按钮：**
- 使用 `GestureDetector` 的 `onLongPress`
- 弹出 PopupMenu：`复制全文`
- 复制到剪贴板后显示 SnackBar："已复制到剪贴板"
- 使用 `Clipboard.setData()`

### 6.3 语音消息气泡（录音功能预留）

如果用户使用语音输入，消息气泡显示为语音样式：
```
┌─────────────────────────────┐
│  🎤  [波形动画]  0:03        │
└─────────────────────────────┘
```

- 显示波形动画（5 根竖条，高度随机）
- 显示时长
- 点击可播放（TTS 功能预留，当前版本仅显示波形）
- 左对齐（用户语音消息也左对齐，因为是 AI 可读的内容）

### 6.4 思考动画升级

现有：3 个蓝色圆点闪烁

升级为更丰富的动画：
```
┌─────────────────────────────┐
│  🤖  小智正在思考...          │
│  ●●●  (波浪形跳动)           │
└─────────────────────────────┘
```

- 3 个圆点做波浪形跳动（Y 轴位移 + 缩放）
- 颜色：从 primaryStart 到 primaryEnd 渐变
- 时长：1200ms 循环

---

## 七、功能 6：错误状态增强

### 7.1 错误类型分类

| 错误类型 | 触发条件 | 用户看到的 UI |
|---------|---------|-------------|
| 网络断开 | HTTP 连接失败 | 🔴 "网络不可用" + "重新连接"按钮 |
| Token 过期 | 401 响应 | 🔄 "登录已过期" + "重新登录"按钮 |
| AI 服务不可用 | 后端 500/超时 | 📞 "AI 暂时不可用" + "联系前台"按钮 + 前台电话 |
| ASR 失败 | 语音识别失败 | 🎤 "语音识别失败" + "重试"按钮 + "切换文字输入"按钮 |
| 请求被拒 | 403（未入住） | 🔒 "请先办理入住" + "前往前台"按钮 |

### 7.2 实现

**修改文件：** `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`

在 `ChatStreamError` 事件处理中，根据错误类型渲染不同 UI：

```dart
// 错误消息模型
class ChatError {
  final String type;    // "network" | "auth" | "server" | "asr" | "forbidden"
  final String message; // 用户友好的错误描述
  final String? action; // 按钮文字
  final String? route;  // 点击按钮跳转的路由
  final String? phone;  // 前台电话
}
```

**错误状态 UI：**

```
┌─────────────────────────────────┐
│  🔴 网络不可用                    │
│  请检查网络连接后重试              │
│  ┌───────────────────────────┐  │
│  │     🔄 重新连接            │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

- 错误卡片使用 `error` 背景色 + 红色边框
- 按钮使用 primaryStart 渐变色
- 点击按钮执行对应操作（重连/重新登录/拨打电话）

### 7.3 网络重连逻辑

```dart
// ChatBloc 中新增重连方法
Future<void> _onRetryConnect(RetryConnect event, Emitter<ChatState> emit) async {
  // 1. 尝试重新连接 WebSocket
  // 2. 如果成功，显示"已重连"提示
  // 3. 如果失败，显示"重连失败，请检查网络"
}

// 自动重连：检测到网络恢复时自动重试
// 使用 connectivity_plus 包监听网络状态
```

---

## 八、功能 7：AI 偏好记忆面板

### 8.1 后端

**现有 API 已就绪：**
- `GET /api/ai/preferences` → 返回 `{key: value}` 字典
- `POST /api/ai/preferences` → 保存/更新偏好
- `DELETE /api/ai/preferences/{key}` → 删除偏好

**需要新增：**
```
GET /api/ai/preferences/list
响应：[
  {
    "key": "ac_temp",
    "value": "24",
    "label": "空调温度",
    "icon": "thermostat",
    "category": "environment",
    "updated_at": "2026-06-05T10:00:00"
  },
  ...
]
```

**偏好 Key 映射表：**

| key | label | icon | category |
|-----|-------|------|----------|
| ac_temp | 空调温度 | thermostat | environment |
| ac_mode | 空调模式 | ac_unit | environment |
| curtain | 窗帘开度 | curtain | environment |
| bedside_light | 床头灯 | light | environment |
| bedroom_light | 卧室灯 | light | environment |
| living_light | 客厅灯 | light | environment |

### 8.2 Flutter 前端

**新建页面：** `smartstay-flutter/lib/pages/ai_chat/preference_panel_page.dart`

**路由：** `/ai-chat/preferences`（从 AI 聊天页面右上角菜单进入）

**页面结构：**

```
┌─────────────────────────────────┐
│  ← AI 偏好设置                   │
│─────────────────────────────────│
│  💡 灯光偏好                     │
│  ┌───────────────────────────┐  │
│  │ 床头灯          [开] 🔘   │  │
│  │ 卧室灯          [开] 🔘   │  │
│  │ 客厅灯          [关] 🔘   │  │
│  └───────────────────────────┘  │
│                                 │
│  🌡️ 温度偏好                     │
│  ┌───────────────────────────┐  │
│  │ 空调温度    16°C ←——●→ 30°C│  │
│  │ 当前: 24°C                 │  │
│  └───────────────────────────┘  │
│                                 │
│  🪟 窗帘偏好                     │
│  ┌───────────────────────────┐  │
│  │ 窗帘开度    0% ←——●→ 100% │  │
│  │ 当前: 80%                  │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │     🗑️ 清除所有偏好        │  │
│  └───────────────────────────┘  │
│                                 │
│  💡 这些偏好会被 AI 自动应用     │
│  在您每次入住时生效              │
└─────────────────────────────────┘
```

**交互逻辑：**
1. 页面加载时调用 `GET /api/ai/preferences/list`
2. 灯光开关 → 切换后立即调用 `POST /api/ai/preferences` 保存
3. 温度滑块 → 拖动停止后 500ms 防抖保存
4. 窗帘滑块 → 同上
5. 清除所有 → 确认弹窗 → 循环调用 `DELETE /api/ai/preferences/{key}`
6. 保存成功 → 显示 SnackBar："偏好已更新，AI 将在下次对话中使用"

**动画：**
- 页面从右侧滑入（GoRouter 的 `CustomTransitionPage` + `SlideTransition`）
- 各偏好分组依次入场（间隔 80ms，从下方滑入 15px + 透明度 0→1）
- 开关切换时有弹性动画（`AnimatedSwitcher` + `ScaleTransition`）

### 8.3 入口设计

在 AI 聊天页面右上角（历史记录图标旁边）新增一个齿轮图标：
- 点击后从右侧滑入偏好面板页面
- 如果用户没有设置任何偏好，齿轮图标显示一个小红点提示

---

## 九、功能 8：场景化快捷命令

### 9.1 后端

**无需后端改动。** 快捷命令最终转化为自然语言发送给现有 AI 接口，由 LangGraph 路由到对应的 action/knowledge 节点。

### 9.2 Flutter 前端

**新建文件：** `smartstay-flutter/lib/widgets/command_menu.dart`

**触发方式：** 在输入框中输入 `/`

**命令列表：**

| 命令 | 映射文本 | 图标 | 分类 |
|------|---------|------|------|
| `/送水` | "帮我送两瓶矿泉水到房间" | water_drop | 服务 |
| `/打扫` | "帮我打扫房间" | cleaning_services | 服务 |
| `/送物` | "请帮我送物品到房间" | inventory_2 | 服务 |
| `/维修` | "房间设备需要维修" | build | 服务 |
| `/空调` | "帮我调节空调温度" | thermostat | 设备 |
| `/灯光` | "帮我控制灯光" | lightbulb | 设备 |
| `/窗帘` | "帮我控制窗帘" | curtain | 设备 |
| `/退房` | "我想办理退房" | hotel_checkout | 流程 |
| `/延迟` | "我想延迟退房" | schedule | 流程 |
| `/账单` | "查看我的账单" | receipt_long | 查询 |
| `/发票` | "我想开发票" | receipt | 查询 |
| `/叫车` | "帮我叫一辆车" | local_taxi | 出行 |
| `/导航` | "我想去某个地方" | map | 出行 |
| `/Wi-Fi` | "Wi-Fi密码是什么" | wifi | 信息 |
| `/投诉` | "我要投诉" | report | 反馈 |

**命令菜单 UI：**

```
┌─────────────────────────────────┐
│  服务                           │
│  ┌────────┐ ┌────────┐         │
│  │💧 送水  │ │🧹 打扫  │         │
│  └────────┘ └────────┘         │
│  ┌────────┐ ┌────────┐         │
│  │📦 送物  │ │🔧 维修  │         │
│  └────────┘ └────────┘         │
│                                 │
│  设备                           │
│  ┌────────┐ ┌────────┐         │
│  │🌡️ 空调  │ │💡 灯光  │         │
│  └────────┘ └────────┘         │
│  ┌────────┐                    │
│  │🪟 窗帘  │                    │
│  └────────┘                    │
│                                 │
│  流程                           │
│  ┌────────┐ ┌────────┐         │
│  │🏨 退房  │ │⏰ 延迟  │         │
│  └────────┘ └────────┘         │
│                                 │
│  ...更多                        │
└─────────────────────────────────┘
```

**交互逻辑：**
1. 用户在输入框输入 `/`
2. 输入框下方弹出命令菜单（从底部滑入，高度自适应）
3. 继续输入文字 → 实时过滤命令（如输入 `/送` 只显示送水、送物）
4. 点击命令 → 将映射文本填入输入框 → 菜单关闭 → 用户可编辑后发送
5. 点击菜单外区域 → 关闭菜单
6. 按返回键 → 关闭菜单

**过滤逻辑：**
```dart
// 输入 "/送" → 过滤出 name.startsWith("送") 或 label.contains("送")
// 输入 "/空调" → 精确匹配
// 输入 "/" → 显示全部
```

**动画：**
- 菜单弹出：从底部滑入 200ms + 透明度 0→1
- 命令项入场：依次入场，间隔 30ms
- 命令项点击：涟漪效果 + 缩放 0.95→1

### 9.3 输入框 UI 变更

现有输入框：`[麦克风] [输入框] [发送/停止]`

升级后：`[麦克风] [输入框 / 提示"/ 输入命令")] [发送/停止]`

- 输入框 placeholder：当无文字时显示"输入消息..."
- 当输入 `/` 后，placeholder 变为"输入命令..."，并弹出命令菜单
- 命令菜单只在输入 `/` 时显示，输入其他文字时隐藏

---

## 十、实施顺序

| 阶段 | 功能 | 工作量 | 依赖 |
|------|------|--------|------|
| 1 | 气泡优化（时间戳、复制、思考动画） | 1 天 | 无 |
| 2 | 错误状态增强 | 0.5 天 | 无 |
| 3 | 智能快捷短语 | 0.5 天 | 无 |
| 4 | ChatCard 富交互升级 | 2 天 | 后端 metadata 字段 |
| 5 | 回复评价机制 | 1.5 天 | 后端 feedback 表 + API |
| 6 | 语音输入 | 2 天 | 后端 ASR 接口 |
| 7 | AI 偏好记忆面板 | 2 天 | 后端偏好列表 API |
| 8 | 场景化快捷命令 | 1 天 | 无 |

**总计：约 10.5 天**

---

## 十一、文件变更清单

### Flutter 新建文件
- `smartstay-flutter/lib/core/voice_service.dart` — 语音录音服务
- `smartstay-flutter/lib/pages/ai_chat/preference_panel_page.dart` — 偏好面板页面
- `smartstay-flutter/lib/widgets/command_menu.dart` — 快捷命令菜单
- `smartstay-flutter/lib/widgets/voice_wave_animation.dart` — 语音波形动画
- `smartstay-flutter/lib/widgets/feedback_panel.dart` — 评价原因选择面板
- `smartstay-flutter/lib/widgets/error_card.dart` — 错误状态卡片

### Flutter 修改文件
- `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart` — 麦克风按钮、命令菜单集成、齿轮入口
- `smartstay-flutter/lib/blocs/chat/chat_bloc.dart` — 语音识别事件、评价事件、错误类型
- `smartstay-flutter/lib/blocs/chat/chat_event.dart` — 新增事件类型
- `smartstay-flutter/lib/blocs/chat/chat_state.dart` — 新增状态字段
- `smartstay-flutter/lib/widgets/chat_card.dart` — 富交互卡片升级
- `smartstay-flutter/lib/widgets/quick_chips.dart` — 智能动态生成
- `smartstay-flutter/lib/widgets/typing_indicator.dart` — 波浪动画升级
- `smartstay-flutter/lib/core/sse_stream_handler.dart` — 新增 feedback_ready 事件
- `smartstay-flutter/lib/models/chat_card.dart` — metadata 字段

### 后端新建文件
- `backend/app/models/feedback.py` — AIChatFeedback 模型

### 后端修改文件
- `backend/app/models/__init__.py` — 导入新模型
- `backend/app/main.py` — 注册新表
- `backend/app/api/ai.py` — 新增 ASR 接口、feedback 接口、偏好列表接口
- `backend/app/ai/graph.py` — card metadata 字段丰富
