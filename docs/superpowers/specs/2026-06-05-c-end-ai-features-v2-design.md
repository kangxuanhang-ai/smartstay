# C端 AI 功能增强设计文档 V2

> 日期：2026-06-05
> 范围：7 项功能（3 项新功能 + 4 项优化）
> UI 风格：深色主题、渐变、毛玻璃、圆角、柔和阴影
> 原则：不省略任何逻辑，UI 必须美观

---

## 一、设计系统

### 1.1 色彩体系

```
主色渐变：primaryStart=#667EEA(紫蓝) → primaryEnd=#764BA2(深紫)
背景：bgDark=#0F0F23, bgCard=#1A1A2E, bgInput=#16213E
功能色：success=#10B981(绿), warning=#F59E0B(琥珀), error=#EF4444(红), info=#3B82F6(蓝), pricing=#8B5CF6(紫)
文字：textPrimary=#FFFFFF, textSecondary=#9CA3AF, textTertiary=#6B7280
```

### 1.2 圆角与阴影

sm=8px, md=12px, lg=16px, full=999px。soft shadow: black 15%, blur 12, offset(0,4)。

### 1.3 动画规范

| 类型 | 时长 | 曲线 |
|------|------|------|
| 页面转场 | 300ms | easeInOutCubic |
| 卡片展开 | 250ms | easeOutBack |
| 按钮涟漪 | 200ms | easeOut |
| 列表入场 | 300ms | easeOutCubic 50ms间隔 |
| 波形 | 150ms循环 | linear |

---

## 二、功能 1：错误状态分类展示 + 消息重试

### 2.1 错误类型

| 类型 | 触发 | 图标 | 标题 | 按钮 |
|------|------|------|------|------|
| network | SocketException | wifi_off | 网络不可用 | 重新连接 |
| auth | 401(重试后) | lock_outline | 登录已过期 | 重新登录 |
| server | 500/502/503/超时 | cloud_off | AI暂时不可用 | 重试+联系前台 |
| asr | ASR失败 | mic_off | 语音识别失败 | 重试+切换文字 |
| forbidden | 403 | lock | 请先办理入住 | 前往前台 |

### 2.2 ChatError 模型

```dart
class ChatError {
  final String type;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final String? secondaryLabel;
  final VoidCallback? onSecondary;
}
```

### 2.3 错误分类逻辑

在 chat_bloc.dart 的 catch 块中：
- SocketException/HttpException -> network
- 401 -> auth (重试后仍失败)
- 403 -> forbidden
- 500/502/503/TimeoutException -> server
- 其他 -> server (通用)

### 2.4 UI 设计

错误卡片：左边框 3px 红色竖线，背景 #1A1A2E 圆角 16px，图标 20px + 标题白色14px + 描述灰色12px，主按钮渐变背景 + 次按钮描边，入场动画：下方滑入15px + 渐显 300ms。

### 2.5 重试逻辑

- network -> 重新发送上一条用户消息
- auth -> 跳转 /login
- server -> 重新发送 + 显示前台电话
- asr -> 重试录音 或 切换文字输入
- forbidden -> 跳转 /home

---

## 三、功能 2：智能快捷短语

### 3.1 动态生成规则

未登录：酒店有什么设施？/ 怎么预订？/ 酒店在哪里？

未入住：查看账单 / 开发票 / 设施

已入住按时段：
- 早晨：打扫 / 附近美食 / Wi-Fi / 退房时间
- 下午：附近美食 / 送水 / 延迟退房
- 晚间：调空调 / 关窗帘 / 开灯 / 送水

历史关键词优先：有空调历史->空调短语优先，有灯光历史->灯光优先，有工单历史->报修进度优先。去重取前4个。

### 3.2 UI 变更

不再只在 messages.isEmpty 时显示，始终显示在输入框上方。有消息时折叠为一行"快捷提问"展开按钮。入场动画：4个短语依次从下方滑入 50ms间隔。

---

## 四、功能 3：消息长按菜单 + 重新生成

### 4.1 交互规则

| 目标 | 复制 | 重新生成 |
|------|------|---------|
| 用户消息 | 有 | 无 |
| AI消息(最后一条) | 有 | 有 |
| AI消息(非最后) | 有 | 无 |
| 流式中 | 无 | 无 |

### 4.2 重新生成流程

1. ChatRegenerate 事件
2. 找到最后一条用户消息 text
3. 删除最后一条 AI 回复
4. 插入 thinking 消息
5. 用相同 text 重新 sendMessage
6. 正常 SSE 流式渲染

### 4.3 UI

长按气泡缩放 1.0->0.98 100ms。PopupMenu 深色 #1A1A2E 圆角 12px。菜单项带图标：复制(content_copy) / 重新生成(refresh)。复制成功 SnackBar 从底部滑入。

---

## 五、功能 4：斜杠命令菜单

### 5.1 命令列表（15个 6分类）

| 命令 | 映射文本 | 图标 | 分类 |
|------|---------|------|------|
| /送水 | 帮我送两瓶矿泉水到房间 | water_drop | 服务 |
| /打扫 | 帮我打扫房间 | cleaning_services | 服务 |
| /送物 | 请帮我送物品到房间 | inventory_2 | 服务 |
| /维修 | 房间设备需要维修 | build | 服务 |
| /空调 | 帮我调节空调温度 | thermostat | 设备 |
| /灯光 | 帮我控制灯光 | lightbulb | 设备 |
| /窗帘 | 帮我控制窗帘 | curtain | 设备 |
| /退房 | 我想办理退房 | hotel_checkout | 流程 |
| /延迟 | 我想延迟退房 | schedule | 流程 |
| /账单 | 查看我的账单 | receipt_long | 查询 |
| /发票 | 我想开发票 | receipt | 查询 |
| /叫车 | 帮我叫一辆车 | local_taxi | 出行 |
| /导航 | 我想去某个地方 | map | 出行 |
| /Wi-Fi | Wi-Fi密码是什么 | wifi | 信息 |
| /投诉 | 我要投诉 | report | 反馈 |

### 5.2 触发与过滤

输入框文字以 / 开头 -> 弹出菜单。继续输入实时过滤。选择后映射文本填入输入框，关闭菜单，用户可编辑后发送。

### 5.3 UI

位置：输入框正上方。最大高度 300px 可滚动。毛玻璃背景 + #0F0F23半透明。分类标题灰色12px。命令项圆角12px #1A1A2E 网格3列。点击涟漪。入场：底部滑入 200ms。

---

## 六、功能 5：语音输入

### 6.1 后端接口

POST /api/ai/asr。请求：multipart/form-data 字段 file。响应：{"text": "识别文字"}。错误：400无文件 / 413文件过大 / 503服务不可用。

### 6.2 后端实现

接收音频 -> 调用 aliyun asr.py -> 返回文本。音频不持久化。注意：asr.py 源文件丢失需重建。

### 6.3 VoiceService

单例。状态：idle/recording/transcribing/error。方法：startRecording / stopRecording / transcribe / cancelRecording。流：stateStream / durationStream。

流程：检查权限(permission_handler) -> 开始录音(record包 AAC) -> 启动计时器(60秒自动停止) -> 停止 -> 上传ASR -> 返回文字 -> 填入输入框。

### 6.4 麦克风4种状态

| 状态 | UI | 手势 |
|------|-----|------|
| idle | 灰色mic #1f2937圆形 | 长按->开始录音 |
| recording | 红色mic + 波形 + 时长 | 松手->停止+识别 / 上滑50px->取消 |
| transcribing | 蓝色loading + 识别中 | 无 |
| error | 灰色mic + 红点 | 点击->重置idle |

### 6.5 录音交互

长按麦克风 -> 录音覆盖层（波形+时长+上滑取消提示）。松手(按钮区) -> 停止+识别 -> 文字填入。松手(上滑50px) -> 取消。不足1秒 -> "录音时间太短"。

### 6.6 波形动画

5根竖条 宽3px 间距3px。高度6-24px 每150ms随机。颜色 primaryStart->primaryEnd 渐变。总宽30px居中。

---

## 七、功能 6：AI 偏好记忆面板

### 7.1 后端接口

GET /api/ai/preferences/list -> 带label/icon/category的结构化数据。现有：GET/POST/DELETE /api/ai/preferences。

### 7.2 偏好Key

| key | label | 类型 | 范围 |
|-----|-------|------|------|
| ac_temp | 空调温度 | 滑块 | 16-30 |
| ac_mode | 空调模式 | 开关 | cool/heat |
| curtain | 窗帘开度 | 滑块 | 0-100 |
| bedside_light | 床头灯 | 开关 | on/off |
| bedroom_light | 卧室灯 | 开关 | on/off |
| living_light | 客厅灯 | 开关 | on/off |

### 7.3 UI

分组卡片圆角16px #1A1A2E。灯光分组3个开关项。温度分组滑块(蓝->红渐变)+空调模式开关。窗帘分组滑块(灰->蓝)。底部清除所有按钮+说明文字。

### 7.4 交互

加载：GET preferences -> 填充初始值。灯光开关：立即POST -> SnackBar。温度/窗帘滑块：500ms防抖POST。清除所有：确认弹窗 -> 循环DELETE -> 刷新。

### 7.5 入口

AI聊天页右上角齿轮图标。路由：/ai-chat/preferences。页面右侧滑入 300ms。未设置过偏好时齿轮显示小红点。

---

## 八、功能 7：卡片富交互升级

### 8.1 后端metadata

deviceControl: {device, value, device_states}
workOrder: {order_id, type, status, content}

### 8.2 deviceControl 卡片

温度：只读滑块(蓝->红渐变) + 当前值。灯光：3个开关状态图标。窗帘：只读滑块+当前值。底部"查看房间控制"导航链接。

### 8.3 workOrder 卡片

3步进度条(已提交->处理中->已完成)。当前步骤高亮 #10B981。工单号显示。底部"查看工单详情"导航。

### 8.4 pricing 卡片

当前价 vs 建议价并排。柱状图对比。变化百分比标签(绿涨红跌)。原因说明。

### 8.5 入场动画

高度0+opacity0 -> 完整高度+opacity1。250ms easeOutBack。

---

## 九、ChatState 扩展

新增字段：chatError (ChatError?) / isRecording (bool) / recordingDuration (int) / isTranscribing (bool)

---

## 十、ChatEvent 扩展

新增事件：ChatRegenerate / ChatVoiceRecordingStarted / ChatVoiceRecordingStopped / ChatVoiceTranscribeRequested(audioPath) / ChatVoiceRecordingCancelled / ChatErrorDismissed

---

## 十一、文件变更清单

### 后端新建
- backend/app/aliyun/asr.py (重建)

### 后端修改
- backend/app/api/ai.py (ASR接口 + 偏好列表)
- backend/app/ai/graph.py (card metadata)

### Flutter 新建
- lib/core/voice_service.dart
- lib/widgets/voice_wave_animation.dart
- lib/widgets/command_menu.dart
- lib/widgets/error_card.dart
- lib/pages/ai_chat/preference_panel_page.dart

### Flutter 修改
- lib/pages/ai_chat/ai_chat_page.dart (麦克风/命令/长按/齿轮)
- lib/blocs/chat/chat_bloc.dart (语音/重试/regenerate/错误)
- lib/blocs/chat/chat_event.dart (6个新事件)
- lib/blocs/chat/chat_state.dart (4个新字段 + ChatError)
- lib/widgets/chat_card.dart (富交互升级)
- lib/widgets/quick_chips.dart (动态生成 + 始终可见)
- lib/app.dart (注册偏好路由)

---

## 十二、实施顺序

| 阶段 | 功能 | 工作量 | 依赖 |
|------|------|--------|------|
| 1 | 错误状态+重试 | 1天 | 无 |
| 2 | 智能快捷短语 | 0.5天 | 无 |
| 3 | 消息长按+重新生成 | 1天 | 无 |
| 4 | 斜杠命令菜单 | 1天 | 无 |
| 5 | 语音输入 | 2天 | 后端ASR |
| 6 | AI偏好面板 | 1.5天 | 后端偏好API |
| 7 | 卡片富交互 | 1.5天 | 后端metadata |

总计：约 8.5 天
