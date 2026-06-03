# C 端语音输入功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 C 端 AI 聊天新增语音输入，住客点击麦克风录音，阿里云 ASR 识别为文字填入输入框。

**Architecture:** 前端用 `record` 包录音 → 上传到后端 → 后端调阿里云一句话识别 REST API → 返回文字。录音在内存中处理，不落盘。

**Tech Stack:** Flutter `record` + `permission_handler`，FastAPI `UploadFile`，阿里云 NLS REST API，`httpx`

---

## 文件结构

### 新建文件
- `backend/app/aliyun/asr.py` — 阿里云 ASR 服务封装
- `smartstay-flutter/lib/services/voice_service.dart` — 录音服务封装

### 修改文件
- `backend/app/core/config.py` — 新增 `ALIYUN_ASR_APP_KEY`
- `backend/app/api/ai.py` — 新增 `POST /api/ai/transcribe` 端点
- `smartstay-flutter/lib/blocs/chat/chat_event.dart` — 新增 3 个事件类
- `smartstay-flutter/lib/blocs/chat/chat_state.dart` — ChatState 新增 3 个字段
- `smartstay-flutter/lib/blocs/chat/chat_bloc.dart` — 新增录音+识别逻辑
- `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart` — 麦克风按钮交互 + 录音状态 UI

---

## Task 1: 后端配置 + ASR 服务

### 1.1 新增配置项

**文件:** `backend/app/core/config.py:14-18`

在阿里云配置区块新增 `ALIYUN_ASR_APP_KEY`：

```python
# 阿里云配置
ALIYUN_ACCESS_KEY_ID: str = ""
ALIYUN_ACCESS_KEY_SECRET: str = ""
ALIYUN_REGION_ID: str = "cn-shanghai"
ALIYUN_FACE_DB_NAME: str = "smartstay_faces"
ALIYUN_ASR_APP_KEY: str = ""  # 智能语音交互项目 App Key
```

### 1.2 创建 ASR 服务

**文件:** 创建 `backend/app/aliyun/asr.py`

使用阿里云**实时语音识别 REST API**（`nls-gateway`），支持直接传入音频字节，无需 OSS。

```python
"""阿里云实时语音识别（NLS REST API）封装"""

import asyncio
import base64
import hashlib
import hmac
import time
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

import httpx

from app.core.config import settings

# 阿里云 NLS 实时语音识别 REST API
_ASR_URL = "https://nls-gateway.cn-shanghai.aliyuncs.com/streaming/v1/asr"
_TOKEN_URL = "https://nls-meta.cn-shanghai.aliyuncs.com/"

# 音频格式映射
_FORMAT_MAP = {
    "m4a": "aac",
    "aac": "aac",
    "wav": "pcm",
    "mp3": "mp3",
    "ogg": "ogg",
    "amr": "amr",
}


async def _get_token() -> str:
    """获取阿里云 NLS Access Token"""
    params = {
        "Action": "CreateToken",
        "AccessKeyId": settings.ALIYUN_ACCESS_KEY_ID,
        "Format": "JSON",
        "RegionId": settings.ALIYUN_REGION_ID,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(int(time.time() * 1000)),
        "SignatureVersion": "1.0",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2019-02-28",
    }

    sorted_params = sorted(params.items())
    query_string = urlencode(sorted_params, quote_via=quote)
    string_to_sign = f"GET&%2F&{quote(query_string, safe='')}"
    sign_key = settings.ALIYUN_ACCESS_KEY_SECRET + "&"
    signature = base64.b64encode(
        hmac.new(sign_key.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()
    params["Signature"] = signature

    async with httpx.AsyncClient() as client:
        resp = await client.get(_TOKEN_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data["Token"]["Id"]


async def transcribe_audio(audio_bytes: bytes, audio_format: str = "m4a") -> str:
    """
    调用阿里云实时语音识别 REST API，返回识别文字。

    Args:
        audio_bytes: 音频文件字节数据
        audio_format: 音频格式 (m4a/wav/mp3)

    Returns:
        识别出的文字

    Raises:
        ValueError: 音频为空或识别结果为空
        RuntimeError: ASR 服务调用失败
    """
    if not audio_bytes:
        raise ValueError("音频数据为空")

    if not settings.ALIYUN_ASR_APP_KEY:
        raise RuntimeError("ALIYUN_ASR_APP_KEY 未配置")

    token = await _get_token()

    nls_format = _FORMAT_MAP.get(audio_format, "aac")
    audio_b64 = base64.b64encode(audio_bytes).decode()

    payload = {
        "appkey": settings.ALIYUN_ASR_APP_KEY,
        "token": token,
        "format": nls_format,
        "sample_rate": 16000,
        "enable_punctuation_prediction": True,
        "enable_inverse_text_normalization": True,
        "enable_voice_detection": True,
    }

    headers = {
        "Content-Type": "application/json",
    }

    # 实时 ASR REST API: POST 音频数据，同步返回结果
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _ASR_URL,
            params=payload,
            content=audio_b64,
            headers=headers,
        )
        resp.raise_for_status()
        result = resp.json()

    if result.get("status") != 20000000:
        raise RuntimeError(f"ASR 识别失败: {result.get('message', '未知错误')}")

    text = result.get("result", "")
    if not text:
        raise ValueError("未识别到语音内容")

    return text
```

- [ ] **Step 1: 修改 config.py**

在 `ALIYUN_FACE_DB_NAME` 下方新增一行：
```python
ALIYUN_ASR_APP_KEY: str = ""  # 智能语音交互项目 App Key
```

- [ ] **Step 2: 创建 asr.py**

创建 `backend/app/aliyun/asr.py`，内容如上。

- [ ] **Step 3: 验证语法**

Run: `cd backend && poetry run python -m py_compile app/aliyun/asr.py`
Expected: 无输出（编译成功）

- [ ] **Step 4: 提交**

```bash
git add backend/app/core/config.py backend/app/aliyun/asr.py
git commit -m "feat(backend): add Aliyun ASR service and config"
```

---

## Task 2: 后端 transcribe 端点

**文件:** `backend/app/api/ai.py:1-4` (imports) + 文件末尾 (新端点)

- [ ] **Step 1: 添加 import**

在 `ai.py` 文件顶部 import 区域，在现有 import 之后新增：

```python
from app.aliyun.asr import transcribe_audio
```

- [ ] **Step 2: 添加端点**

在 `ai.py` 文件末尾（`set_safety_threshold` 函数之后）添加：

```python
@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    current_user: Guest = Depends(get_current_user),
):
    """语音识别：接收音频文件，返回识别文字"""
    # 校验文件大小（10MB）
    contents = await audio.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="音频文件过大，最大 10MB")

    # 校验格式
    allowed_formats = {"m4a", "wav", "mp3", "aac", "ogg", "amr"}
    ext = audio.filename.rsplit(".", 1)[-1].lower() if audio.filename and "." in audio.filename else ""
    if ext not in allowed_formats:
        raise HTTPException(status_code=400, detail=f"不支持的音频格式: {ext}")

    try:
        text = await transcribe_audio(contents, audio_format=ext)
        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 验证语法**

Run: `cd backend && poetry run python -m py_compile app/api/ai.py`
Expected: 无输出（编译成功）

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/ai.py
git commit -m "feat(backend): add POST /api/ai/transcribe endpoint"
```

---

## Task 3: Flutter 录音服务

**文件:** 创建 `smartstay-flutter/lib/services/voice_service.dart`

- [ ] **Step 1: 创建 voice_service.dart**

```dart
import 'dart:async';
import 'package:record/record.dart';
import 'package:permission_handler/permission_handler.dart';

class VoiceService {
  final AudioRecorder _recorder = AudioRecorder();
  Timer? _durationTimer;
  int _duration = 0;

  int get duration => _duration;

  Future<bool> requestPermission() async {
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  Future<bool> hasPermission() async {
    final status = await Permission.microphone.status;
    return status.isGranted;
  }

  Future<void> startRecording() async {
    final hasPerm = await hasPermission();
    if (!hasPerm) {
      final granted = await requestPermission();
      if (!granted) {
        throw Exception('麦克风权限被拒绝');
      }
    }

    _duration = 0;

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        sampleRate: 16000,
        numChannels: 1,
      ),
      path: '',  // 使用内存模式，不写文件
    );

    _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _duration++;
    });
  }

  Future<String?> stopRecording() async {
    _durationTimer?.cancel();
    _durationTimer = null;
    final path = await _recorder.stop();
    return path;
  }

  Future<void> cancelRecording() async {
    _durationTimer?.cancel();
    _durationTimer = null;
    await _recorder.cancel();
  }

  Future<bool> isRecording() async {
    return _recorder.isRecording();
  }

  void dispose() {
    _durationTimer?.cancel();
    _recorder.dispose();
  }
}
```

- [ ] **Step 2: 验证编译**

Run: `cd smartstay-flutter && flutter analyze lib/services/voice_service.dart`
Expected: No issues found

- [ ] **Step 3: 提交**

```bash
git add smartstay-flutter/lib/services/voice_service.dart
git commit -m "feat(flutter): add VoiceService for audio recording"
```

---

## Task 4: Flutter BLoC 事件和状态

### 4.1 新增事件

**文件:** `smartstay-flutter/lib/blocs/chat/chat_event.dart`

- [ ] **Step 1: 添加 3 个事件类**

在文件末尾追加：

```dart
class ChatVoiceRecordStarted {
  const ChatVoiceRecordStarted();
}

class ChatVoiceRecordStopped {
  const ChatVoiceRecordStopped();
}

class ChatVoiceTranscribed {
  final String text;
  const ChatVoiceTranscribed(this.text);
}
```

### 4.2 新增状态字段

**文件:** `smartstay-flutter/lib/blocs/chat/chat_state.dart`

- [ ] **Step 2: 修改 ChatState**

在 `ChatState` 类中新增 3 个字段，更新构造函数和 `copyWith`：

```dart
class ChatState {
  final List<ChatMessage> messages;
  final bool isStreaming;
  final String? error;
  final List<Map<String, dynamic>> sessions;
  final String? currentSessionId;
  final bool isRecording;
  final bool isTranscribing;
  final int recordingDuration;

  const ChatState({
    this.messages = const [],
    this.isStreaming = false,
    this.error,
    this.sessions = const [],
    this.currentSessionId,
    this.isRecording = false,
    this.isTranscribing = false,
    this.recordingDuration = 0,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isStreaming,
    String? error,
    List<Map<String, dynamic>>? sessions,
    String? currentSessionId,
    bool? isRecording,
    bool? isTranscribing,
    int? recordingDuration,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isStreaming: isStreaming ?? this.isStreaming,
      error: error,
      sessions: sessions ?? this.sessions,
      currentSessionId: currentSessionId ?? this.currentSessionId,
      isRecording: isRecording ?? this.isRecording,
      isTranscribing: isTranscribing ?? this.isTranscribing,
      recordingDuration: recordingDuration ?? this.recordingDuration,
    );
  }
}
```

- [ ] **Step 3: 验证编译**

Run: `cd smartstay-flutter && flutter analyze lib/blocs/chat/`
Expected: No issues found

- [ ] **Step 4: 提交**

```bash
git add smartstay-flutter/lib/blocs/chat/chat_event.dart smartstay-flutter/lib/blocs/chat/chat_state.dart
git commit -m "feat(flutter): add voice recording events and state fields"
```

---

## Task 5: Flutter BLoC 录音逻辑

**文件:** `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`

- [ ] **Step 1: 添加 import**

在文件顶部 import 区域新增：

```dart
import '../../services/voice_service.dart';
import 'package:dio/dio.dart';
```

- [ ] **Step 2: 添加字段和事件注册**

在 `ChatBloc` 类中：

```dart
class ChatBloc extends Bloc<Object, ChatState> {
  ChatBloc() : super(const ChatState()) {
    on<ChatMessageSent>(_onSend);
    on<ChatStreamCancelled>(_onCancel);
    on<ChatSessionsLoadRequested>(_onLoadSessions);
    on<ChatSessionSwitchRequested>(_onSwitchSession);
    on<ChatNewSessionRequested>(_onNewSession);
    on<ChatVoiceRecordStarted>(_onVoiceStart);
    on<ChatVoiceRecordStopped>(_onVoiceStop);
  }

  final _api = ApiClient();
  final _streamService = ChatStreamService();
  final _voiceService = VoiceService();
  bool _pendingNewSession = false;
```

- [ ] **Step 3: 添加录音事件处理方法**

在 `_onNewSession` 方法之后、`close()` 方法之前添加：

```dart
  Timer? _recordingTimer;

  void _startDurationTimer() {
    _recordingTimer?.cancel();
    _recordingTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      final dur = state.recordingDuration + 1;
      if (dur >= 60) {
        add(const ChatVoiceRecordStopped());
      } else {
        emit(state.copyWith(recordingDuration: dur));
      }
    });
  }

  Future<void> _onVoiceStart(
    ChatVoiceRecordStarted event,
    Emitter<ChatState> emit,
  ) async {
    try {
      await _voiceService.startRecording();
      emit(state.copyWith(isRecording: true, recordingDuration: 0, error: null));
      _startDurationTimer();
    } catch (e) {
      final msg = e.toString().contains('权限') ? '请在设置中开启麦克风权限' : '录音失败，请重试';
      emit(state.copyWith(error: msg));
    }
  }

  Future<void> _onVoiceStop(
    ChatVoiceRecordStopped event,
    Emitter<ChatState> emit,
  ) async {
    _recordingTimer?.cancel();
    _recordingTimer = null;

    try {
      final path = await _voiceService.stopRecording();
      emit(state.copyWith(isRecording: false, isTranscribing: true));

      if (path == null || path.isEmpty) {
        emit(state.copyWith(isTranscribing: false, error: '录音失败，请重试'));
        return;
      }

      // 检查录音时长
      if (_voiceService.duration < 1) {
        emit(state.copyWith(isTranscribing: false, error: '录音时间太短'));
        return;
      }

      // 上传音频到后端
      final formData = FormData.fromMap({
        'audio': await MultipartFile.fromFile(path, filename: 'recording.m4a'),
      });

      final resp = await _api.post('/api/ai/transcribe', data: formData);
      final text = resp.data['text'] as String?;

      if (text == null || text.isEmpty) {
        emit(state.copyWith(isTranscribing: false, error: '未识别到语音内容'));
        return;
      }

      emit(state.copyWith(isTranscribing: false, transcribedText: text));
    } catch (e) {
      emit(state.copyWith(
        isTranscribing: false,
        error: e is DioException ? '识别失败，请重试' : '识别失败: $e',
      ));
    }
  }
```

- [ ] **Step 4: 更新 close()**

```dart
  @override
  Future<void> close() {
    _recordingTimer?.cancel();
    _streamService.cancel();
    _voiceService.dispose();
    return super.close();
  }
```

- [ ] **Step 5: 验证编译**

Run: `cd smartstay-flutter && flutter analyze lib/blocs/chat/chat_bloc.dart`
Expected: No issues found

- [ ] **Step 6: 提交**

```bash
git add smartstay-flutter/lib/blocs/chat/chat_bloc.dart
git commit -m "feat(flutter): add voice recording logic to ChatBloc"
```

---

## Task 6: Flutter 麦克风按钮 UI

**文件:** `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: 添加 import**

在文件顶部新增：

```dart
import 'dart:async';
```

- [ ] **Step 2: 替换麦克风按钮**

将第 283-287 行的静态麦克风按钮：

```dart
                Container(
                  width: 40, height: 40,
                  decoration: const BoxDecoration(color: _card, shape: BoxShape.circle),
                  child: const Icon(Icons.mic, color: _muted, size: 20),
                ),
```

替换为：

```dart
                BlocBuilder<ChatBloc, ChatState>(
                  buildWhen: (prev, curr) =>
                      prev.isRecording != curr.isRecording ||
                      prev.isTranscribing != curr.isTranscribing ||
                      prev.recordingDuration != curr.recordingDuration,
                  builder: (context, state) {
                    if (state.isTranscribing) {
                      return Container(
                        width: 40, height: 40,
                        decoration: const BoxDecoration(color: _card, shape: BoxShape.circle),
                        child: const SizedBox(
                          width: 18, height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: _muted),
                        ),
                      );
                    }
                    return GestureDetector(
                      onTap: () {
                        final bloc = context.read<ChatBloc>();
                        if (state.isRecording) {
                          bloc.add(const ChatVoiceRecordStopped());
                        } else {
                          bloc.add(const ChatVoiceRecordStarted());
                        }
                      },
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        width: 40, height: 40,
                        decoration: BoxDecoration(
                          color: state.isRecording ? const Color(0xFFef4444) : _card,
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          state.isRecording ? Icons.stop_rounded : Icons.mic,
                          color: state.isRecording ? Colors.white : _muted,
                          size: 20,
                        ),
                      ),
                    );
                  },
                ),
```

- [ ] **Step 3: 修改输入栏 — 录音/识别中隐藏 TextField**

将第 264-279 行的 `Expanded` 包裹的 TextField 区域：

```dart
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: _card, borderRadius: BorderRadius.circular(12),
                    ),
                    child: TextField(
                      controller: _textCtrl,
                      onSubmitted: (_) => _send(),
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                      decoration: const InputDecoration(
                        hintText: '输入您的需求...',
                        hintStyle: TextStyle(color: _muted),
                        border: InputBorder.none,
                      ),
                    ),
                  ),
                ),
```

替换为：

```dart
                Expanded(
                  child: BlocBuilder<ChatBloc, ChatState>(
                    buildWhen: (prev, curr) =>
                        prev.isRecording != curr.isRecording ||
                        prev.isTranscribing != curr.isTranscribing ||
                        prev.recordingDuration != curr.recordingDuration,
                    builder: (context, state) {
                      final isVoiceActive = state.isRecording || state.isTranscribing;
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        decoration: BoxDecoration(
                          color: _card, borderRadius: BorderRadius.circular(12),
                        ),
                        child: isVoiceActive
                            ? Center(
                                child: Text(
                                  state.isRecording
                                      ? '录音中 ${_formatDuration(state.recordingDuration)}...'
                                      : '识别中...',
                                  style: const TextStyle(color: _muted, fontSize: 14),
                                ),
                              )
                            : TextField(
                                controller: _textCtrl,
                                onSubmitted: (_) => _send(),
                                style: const TextStyle(color: Colors.white, fontSize: 14),
                                decoration: const InputDecoration(
                                  hintText: '输入您的需求...',
                                  hintStyle: TextStyle(color: _muted),
                                  border: InputBorder.none,
                                ),
                              ),
                      );
                    },
                  ),
                ),
```

- [ ] **Step 4: 修改发送按钮 — 录音/识别中禁用**

将第 289-310 行的发送按钮 `BlocBuilder` 的 `buildWhen` 和 `builder`：

```dart
                BlocBuilder<ChatBloc, ChatState>(
                  buildWhen: (prev, curr) => prev.isStreaming != curr.isStreaming,
                  builder: (context, state) {
```

替换为：

```dart
                BlocBuilder<ChatBloc, ChatState>(
                  buildWhen: (prev, curr) =>
                      prev.isStreaming != curr.isStreaming ||
                      prev.isRecording != curr.isRecording ||
                      prev.isTranscribing != curr.isTranscribing,
                  builder: (context, state) {
                    if (state.isRecording || state.isTranscribing) {
                      return const SizedBox(width: 40, height: 40);  // 隐藏发送按钮
                    }
```

- [ ] **Step 5: 添加格式化辅助函数**

在 `_AIChatPageState` 类中（`_scrollToBottom` 方法之后）添加：

```dart
  String _formatDuration(int seconds) {
    final m = (seconds ~/ 60).toString().padLeft(2, '0');
    final s = (seconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }
```

- [ ] **Step 6: 监听 ChatVoiceTranscribed 事件填入输入框**

在 `_buildBody` 方法的 `Column` children 中，`BlocBuilder<ChatBloc, ChatState>`（聊天消息列表）之前，添加一个 `BlocListener`：

将 `Expanded` 包裹的 `BlocBuilder<ChatBloc, ChatState>` (第 122-239 行) 改为用 `BlocListener` 包裹：

在 `_buildBody` 的 `Column` children 中，在 `Expanded` 之前插入：

```dart
          BlocListener<ChatBloc, ChatState>(
            listenWhen: (prev, curr) => !prev.isTranscribing && curr.isTranscribing == false && prev.isTranscribing,
            listener: (context, state) {
              // 识别完成后，如果 error 不为空则显示 SnackBar
              if (state.error != null) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(state.error!), backgroundColor: const Color(0xFFef4444)),
                );
              }
            },
            child: const SizedBox.shrink(),
          ),
```

实际上更好的方式是在 `_onVoiceStop` 中通过 stream controller 暴露识别结果。但为了保持简洁，我们用一个更简单的方案：在 `_AIChatPageState` 中监听 BLoC 状态变化。

在 `_AIChatPageState` 的 `build` 方法中，将整个 body 用 `BlocListener` 包裹：

```dart
  @override
  Widget build(BuildContext context) {
    final isLoggedIn = context.watch<AuthBloc>().state.status == AuthStatus.authenticated;

    return BlocListener<ChatBloc, ChatState>(
      listenWhen: (prev, curr) =>
          prev.isTranscribing && !curr.isTranscribing && curr.error != null,
      listener: (context, state) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(state.error!), backgroundColor: const Color(0xFFef4444)),
        );
        context.read<ChatBloc>().add(const ChatClearError());
      },
      child: Scaffold(
        backgroundColor: _bg,
        body: isLoggedIn ? _buildBody() : const AuthPrompt.overlay(
          icon: '🤖', title: 'AI 虚拟管家',
          description: '登录后即可享受智能对话\n控制设备 · 查询信息 · 提交服务'),
      ),
    );
  }
```

等等，这需要一个 `ChatClearError` 事件。更简单的方案：让 `_onVoiceStop` 成功时直接 emit 一个带 transcribedText 的状态，UI 读取后填入输入框。

**更好的方案：** 在 ChatState 中加一个 `transcribedText` 字段，UI 监听到变化后填入 TextField 并清除。

让我重新调整 Task 5 和 Task 6 的实现：

- [ ] **Step 6 (revised): 修改 ChatState 增加 transcribedText**

在 `chat_state.dart` 的 `ChatState` 中新增：

```dart
  final String? transcribedText;
```

构造函数和 `copyWith` 中也要加上。

- [ ] **Step 7: 在 _onVoiceStop 成功时设置 transcribedText**

将 Task 5 Step 3 中的成功分支改为：

```dart
      emit(state.copyWith(isTranscribing: false, transcribedText: text));
```

- [ ] **Step 8: UI 监听 transcribedText 填入输入框**

在 `_AIChatPageState.build` 中用 `BlocListener`：

```dart
  @override
  Widget build(BuildContext context) {
    final isLoggedIn = context.watch<AuthBloc>().state.status == AuthStatus.authenticated;

    return BlocListener<ChatBloc, ChatState>(
      listenWhen: (prev, curr) =>
          (prev.isTranscribing && !curr.isTranscribing) ||
          (prev.transcribedText != curr.transcribedText && curr.transcribedText != null),
      listener: (context, state) {
        if (state.transcribedText != null && state.transcribedText!.isNotEmpty) {
          _textCtrl.text = state.transcribedText!;
          _textCtrl.selection = TextSelection.fromPosition(
            TextPosition(offset: _textCtrl.text.length),
          );
          // 清除 transcribedText
          context.read<ChatBloc>().add(const ChatClearTranscribedText());
        }
        if (state.error != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(state.error!), backgroundColor: const Color(0xFFef4444)),
          );
          context.read<ChatBloc>().add(const ChatClearError());
        }
      },
      child: Scaffold(
        backgroundColor: _bg,
        body: isLoggedIn ? _buildBody() : const AuthPrompt.overlay(
          icon: '🤖', title: 'AI 虚拟管家',
          description: '登录后即可享受智能对话\n控制设备 · 查询信息 · 提交服务'),
      ),
    );
  }
```

- [ ] **Step 9: 添加 ChatClearTranscribedText 和 ChatClearError 事件**

在 `chat_event.dart` 中添加：

```dart
class ChatClearTranscribedText {
  const ChatClearTranscribedText();
}

class ChatClearError {
  const ChatClearError();
}
```

在 `chat_bloc.dart` 中注册：

```dart
    on<ChatClearTranscribedText>((event, emit) {
      emit(state.copyWith(transcribedText: null));
    });
    on<ChatClearError>((event, emit) {
      emit(state.copyWith(error: null));
    });
```

- [ ] **Step 10: 验证编译**

Run: `cd smartstay-flutter && flutter analyze`
Expected: No issues found

- [ ] **Step 11: 提交**

```bash
git add smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart \
       smartstay-flutter/lib/blocs/chat/chat_event.dart \
       smartstay-flutter/lib/blocs/chat/chat_state.dart \
       smartstay-flutter/lib/blocs/chat/chat_bloc.dart
git commit -m "feat(flutter): add voice input UI with mic button and transcription"
```

---

## Task 7: 端到端验证

- [ ] **Step 1: 后端类型检查**

Run: `cd backend && poetry run python -m py_compile app/main.py`
Expected: 无输出

- [ ] **Step 2: 后端测试**

Run: `cd backend && poetry run pytest -x -q`
Expected: 全部通过

- [ ] **Step 3: Flutter 静态分析**

Run: `cd smartstay-flutter && flutter analyze`
Expected: No issues found

- [ ] **Step 4: 更新 feature_list.json**

将语音输入功能添加到 feature_list.json，状态设为 `done`。

- [ ] **Step 5: 更新 progress.md 和 session-handoff.md**

记录完成情况。

- [ ] **Step 6: 最终提交**

```bash
git add feature_list.json progress.md session-handoff.md
git commit -m "docs: mark voice input feature as done"
```
