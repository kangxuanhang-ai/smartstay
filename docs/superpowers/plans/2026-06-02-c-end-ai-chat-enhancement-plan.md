# C 端 AI 聊天增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the C-end Flutter AI chat with UX improvements (stop button, typing indicator, tool status, quick chips), new features (Markdown, interactive cards, voice input, multi-session history), and code refactoring (SSE extraction, typed cards, ChatBloc split).

**Architecture:** Three phases implemented sequentially. Phase 1 is pure C-end Flutter (no backend changes). Phase 2 adds 2 backend endpoints + 4 Flutter dependencies. Phase 3 refactors internal code with no user-visible changes. All phases modify `smartstay-flutter/lib/` files.

**Tech Stack:** Flutter 3.35+, flutter_bloc 9.x, http, dart:html (web), flutter_markdown, record, permission_handler, FastAPI (backend additions)

**Verification command (run after every task):**
```bash
cd smartstay-flutter && flutter analyze
```

**Spec:** `docs/superpowers/specs/2026-06-02-c-end-ai-chat-enhancement-design.md`

---

## File Map

### Phase 1 — UX Optimization
| File | Action | Responsibility |
|------|--------|---------------|
| `lib/blocs/chat/chat_event.dart` | Modify | Add `ChatStreamCancelled` event |
| `lib/blocs/chat/chat_state.dart` | Modify | Add `isThinking` to ChatMessage |
| `lib/blocs/chat/chat_bloc.dart` | Modify | Handle cancel + set isThinking |
| `lib/widgets/typing_indicator.dart` | Create | Three-dot pulsing animation |
| `lib/widgets/quick_chips.dart` | Create | Context-aware suggestion chips |
| `lib/pages/ai_chat/ai_chat_page.dart` | Modify | Stop button, typing indicator, tool status, quick chips |

### Phase 2 — Feature Enhancement
| File | Action | Responsibility |
|------|--------|---------------|
| `pubspec.yaml` | Modify | Add flutter_markdown, record, permission_handler |
| `lib/blocs/chat/chat_event.dart` | Modify | Add session/voice events |
| `lib/blocs/chat/chat_state.dart` | Modify | Add isRecording, sessions, currentSessionId |
| `lib/blocs/chat/chat_bloc.dart` | Modify | Voice recording + session management |
| `lib/widgets/chat_card.dart` | Create | Interactive card widgets |
| `lib/pages/ai_chat/ai_chat_page.dart` | Modify | Markdown, cards, voice button, history |
| `lib/pages/ai_chat/session_list_page.dart` | Create | Session history bottom sheet |
| `backend/app/api/ai.py` | Modify | Add /transcribe and /sessions endpoints |

### Phase 3 — Code Refactoring
| File | Action | Responsibility |
|------|--------|---------------|
| `lib/models/chat_card.dart` | Create | Type-safe ChatCard model |
| `lib/core/sse_stream_handler.dart` | Create | Unified SSE parsing |
| `lib/services/chat_stream_service.dart` | Create | HTTP + SSE + auth refresh |
| `lib/blocs/chat/chat_state.dart` | Modify | Use ChatCard instead of Map |
| `lib/blocs/chat/chat_bloc.dart` | Modify | Delegate to ChatStreamService |

---

## Phase 1: UX Optimization

### Task 1: Stop/Cancel Button

**Files:**
- Modify: `smartstay-flutter/lib/blocs/chat/chat_event.dart`
- Modify: `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Add ChatStreamCancelled event**

In `smartstay-flutter/lib/blocs/chat/chat_event.dart`, add after the existing `ChatMessageSent` class:

```dart
class ChatStreamCancelled {
  const ChatStreamCancelled();
}
```

Full file after edit:

```dart
class ChatMessageSent {
  final String message;
  const ChatMessageSent(this.message);
}

class ChatStreamCancelled {
  const ChatStreamCancelled();
}
```

- [ ] **Step 2: Register cancel handler in ChatBloc**

In `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`, add the event handler registration in the constructor and the cancel handler method.

In the constructor, add after `on<ChatMessageSent>(_onSend);`:

```dart
on<ChatStreamCancelled>(_onCancel);
```

Add the `_onCancel` method before the `close()` method:

```dart
void _onCancel(ChatStreamCancelled event, Emitter<ChatState> emit) {
  _httpSub?.cancel();
  _httpSub = null;
  _webRequest?.abort();
  _webRequest = null;
  emit(state.copyWith(isStreaming: false));
}
```

- [ ] **Step 3: Update AIChatPage input bar to show stop button**

In `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`, find the send button section (the `GestureDetector` with `onTap: _send`) and replace it with a conditional that shows a stop button when streaming.

Replace the last two children of the input bar `Row` (the mic button and send button area):

```dart
// Find this block (the GestureDetector for send):
GestureDetector(
  onTap: _send,
  child: Container(
    width: 40, height: 40,
    decoration: const BoxDecoration(color: _blue, shape: BoxShape.circle),
    child: const Icon(Icons.send, color: Colors.white, size: 18),
  ),
),

// Replace with:
BlocBuilder<ChatBloc, ChatState>(
  buildWhen: (prev, curr) => prev.isStreaming != curr.isStreaming,
  builder: (context, state) {
    if (state.isStreaming) {
      return GestureDetector(
        onTap: () => context.read<ChatBloc>().add(const ChatStreamCancelled()),
        child: Container(
          width: 40, height: 40,
          decoration: const BoxDecoration(color: Color(0xFFef4444), shape: BoxShape.circle),
          child: const Icon(Icons.stop_rounded, color: Colors.white, size: 20),
        ),
      );
    }
    return GestureDetector(
      onTap: _send,
      child: Container(
        width: 40, height: 40,
        decoration: const BoxDecoration(color: _blue, shape: BoxShape.circle),
        child: const Icon(Icons.send, color: Colors.white, size: 18),
      ),
    );
  },
),
```

- [ ] **Step 4: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add smartstay-flutter/lib/blocs/chat/chat_event.dart smartstay-flutter/lib/blocs/chat/chat_bloc.dart smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "feat(chat): add stop/cancel button for streaming responses"
```

---

### Task 2: Typing Indicator

**Files:**
- Modify: `smartstay-flutter/lib/blocs/chat/chat_state.dart`
- Modify: `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`
- Create: `smartstay-flutter/lib/widgets/typing_indicator.dart`
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Add isThinking to ChatMessage**

In `smartstay-flutter/lib/blocs/chat/chat_state.dart`, add `isThinking` field to `ChatMessage`:

```dart
class ChatMessage {
  final String id;
  final bool isUser;
  final String text;
  final List<Map<String, dynamic>> cards;
  final bool isThinking;

  const ChatMessage({
    required this.id,
    required this.isUser,
    this.text = '',
    this.cards = const [],
    this.isThinking = false,
  });
}
```

- [ ] **Step 2: Set isThinking in ChatBloc _onSend**

In `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`, in `_onSend`, when creating the initial AI message, set `isThinking: true`:

Find:
```dart
final aiMsg = ChatMessage(id: aiMsgId, isUser: false);
```

Replace with:
```dart
final aiMsg = ChatMessage(id: aiMsgId, isUser: false, isThinking: true);
```

- [ ] **Step 3: Clear isThinking on first text token**

In both `_sendViaWeb` and `_sendViaDio`, when processing the first `type: "text"` event, set `isThinking: false` on the message.

In `_sendViaWeb`, find the text handling block inside `onProgress.listen`:
```dart
if (type == 'text') {
  final content = (data['content'] ?? '').toString();
  final idx = state.messages.indexWhere((m) => m.id == aiMsgId);
  if (idx == -1) continue;
  final msgs = List<ChatMessage>.from(state.messages);
  msgs[idx] = ChatMessage(
    id: aiMsgId, isUser: false,
    text: msgs[idx].text + content,
    cards: List.from(cards),
  );
```

Replace with:
```dart
if (type == 'text') {
  final content = (data['content'] ?? '').toString();
  final idx = state.messages.indexWhere((m) => m.id == aiMsgId);
  if (idx == -1) continue;
  final msgs = List<ChatMessage>.from(state.messages);
  msgs[idx] = ChatMessage(
    id: aiMsgId, isUser: false,
    text: msgs[idx].text + content,
    cards: List.from(cards),
    isThinking: false,
  );
```

Do the same in the `onLoad.listen` text handling block and in `_sendViaDio`'s `onData` callback for the `'text'` case.

- [ ] **Step 4: Create TypingIndicator widget**

Create `smartstay-flutter/lib/widgets/typing_indicator.dart`:

```dart
import 'package:flutter/material.dart';

class TypingIndicator extends StatefulWidget {
  const TypingIndicator({super.key});

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 48,
      height: 24,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: List.generate(3, (i) {
          return AnimatedBuilder(
            animation: _controller,
            builder: (_, __) {
              final delay = i * 0.2;
              final value = ((_controller.value + delay) % 1.0);
              final opacity = (value < 0.5) ? value * 2 : (1.0 - value) * 2;
              return Opacity(
                opacity: opacity.clamp(0.3, 1.0),
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: Color(0xFF60a5fa),
                    shape: BoxShape.circle,
                  ),
                ),
              );
            },
          );
        }),
      ),
    );
  }
}
```

- [ ] **Step 5: Show TypingIndicator in AIChatPage**

In `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`, in the message rendering `ListView.builder`, find the AI message text rendering:

```dart
if (msg.text.isNotEmpty)
  Text(msg.text, style: TextStyle(
    fontSize: 14, color: isUser ? Colors.white : const Color(0xFFc0c0e0))),
```

Replace with:

```dart
if (msg.isThinking)
  const TypingIndicator()
else if (msg.text.isNotEmpty)
  Text(msg.text, style: TextStyle(
    fontSize: 14, color: isUser ? Colors.white : const Color(0xFFc0c0e0))),
```

Add the import at the top of the file:

```dart
import '../../widgets/typing_indicator.dart';
```

- [ ] **Step 6: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add smartstay-flutter/lib/blocs/chat/chat_state.dart smartstay-flutter/lib/blocs/chat/chat_bloc.dart smartstay-flutter/lib/widgets/typing_indicator.dart smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "feat(chat): add typing indicator with three-dot pulsing animation"
```

---

### Task 3: Tool Call Status Display

**Files:**
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Update card rendering to show loading state**

In `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`, find the card rendering in the message bubble:

```dart
...msg.cards.map((card) => Container(
  margin: const EdgeInsets.only(top: 8),
  padding: const EdgeInsets.all(10),
  decoration: BoxDecoration(
    color: _card, borderRadius: BorderRadius.circular(10)),
  child: Row(children: [
    Text(card['type'] == 'error' ? '❌' : '✅', style: const TextStyle(fontSize: 16)),
    const SizedBox(width: 8),
    Expanded(child: Text(card['title'] ?? '',
      style: const TextStyle(fontSize: 13, color: Colors.white))),
  ]),
)),
```

Replace with:

```dart
...msg.cards.map((card) {
  final isError = card['type'] == 'error';
  return BlocBuilder<ChatBloc, ChatState>(
    buildWhen: (prev, curr) => prev.isStreaming != curr.isStreaming,
    builder: (context, state) {
      final isStreaming = state.isStreaming;
      return Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: _card,
          borderRadius: BorderRadius.circular(10),
          border: isError ? Border.all(color: const Color(0xFFef4444), width: 1) : null,
        ),
        child: Row(children: [
          if (isStreaming)
            const SizedBox(
              width: 16, height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Color(0xFF60a5fa),
              ),
            )
          else
            Text(isError ? '❌' : '✅', style: const TextStyle(fontSize: 16)),
          const SizedBox(width: 8),
          Expanded(child: Text(
            card['title'] ?? '',
            style: TextStyle(
              fontSize: 13,
              color: isError ? const Color(0xFFfca5a5) : Colors.white,
            ),
          )),
        ]),
      );
    },
  );
}),
```

- [ ] **Step 2: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "feat(chat): show loading indicator on cards during streaming"
```

---

### Task 4: Quick Action Chips

**Files:**
- Create: `smartstay-flutter/lib/widgets/quick_chips.dart`
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Create QuickChips widget**

Create `smartstay-flutter/lib/widgets/quick_chips.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../blocs/auth/auth_bloc.dart';
import '../blocs/auth/auth_state.dart';
import '../blocs/room/room_bloc.dart';

class QuickChips extends StatelessWidget {
  final ValueChanged<String> onSelected;

  const QuickChips({super.key, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    final authState = context.watch<AuthBloc>().state;
    final roomState = context.watch<RoomBloc>().state;
    final chips = _getChips(authState, roomState);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: chips.map((text) {
          return GestureDetector(
            onTap: () => onSelected(text),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFF1f2937),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFF2563eb).withOpacity(0.4)),
              ),
              child: Text(
                text,
                style: const TextStyle(fontSize: 13, color: Color(0xFF93c5fd)),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  List<String> _getChips(AuthState auth, RoomState room) {
    if (auth.status != AuthStatus.authenticated) {
      return ['酒店有什么设施？', '怎么预订房间？', '酒店在哪里？'];
    }
    if (room.roomStatus == 'checked_in' || room.roomNumber.isNotEmpty) {
      return ['空调太冷了', '帮我打扫房间', '附近有什么好吃的？', '我想延迟退房'];
    }
    return ['查看我的账单', '怎么开发票？', '酒店有什么设施？'];
  }
}
```

- [ ] **Step 2: Add QuickChips to AIChatPage**

In `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`, add the import:

```dart
import '../../widgets/quick_chips.dart';
```

In `_buildBody()`, add the `QuickChips` widget between the chat messages `Expanded` and the input bar `Container`. Find:

```dart
          ),  // end of Expanded (chat messages)
          // ── Input Bar ──
```

Insert before the input bar:

```dart
          // ── Quick Chips (only when no messages) ──
          BlocBuilder<ChatBloc, ChatState>(
            buildWhen: (prev, curr) => prev.messages.length != curr.messages.length,
            builder: (context, state) {
              if (state.messages.isEmpty) {
                return QuickChips(
                  onSelected: (text) {
                    context.read<ChatBloc>().add(ChatMessageSent(text));
                  },
                );
              }
              return const SizedBox.shrink();
            },
          ),
```

- [ ] **Step 3: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add smartstay-flutter/lib/widgets/quick_chips.dart smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "feat(chat): add context-aware quick action chips"
```

---

**Phase 1 complete. Run full verification:**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors. All 4 UX improvements working: stop button, typing indicator, tool status loading, quick chips.

---

## Phase 2: Feature Enhancement

### Task 5: Add Flutter Dependencies

**Files:**
- Modify: `smartstay-flutter/pubspec.yaml`

- [ ] **Step 1: Add new dependencies**

In `smartstay-flutter/pubspec.yaml`, add to `dependencies`:

```yaml
  flutter_markdown: ^0.7.0
  record: ^5.2.0
  permission_handler: ^11.3.0
```

(`url_launcher` is already in pubspec.yaml.)

- [ ] **Step 2: Install dependencies**

```bash
cd smartstay-flutter && flutter pub get
```

Expected: All dependencies resolved.

- [ ] **Step 3: Commit**

```bash
git add smartstay-flutter/pubspec.yaml smartstay-flutter/pubspec.lock
git commit -m "deps: add flutter_markdown, record, permission_handler"
```

---

### Task 6: Markdown Rendering

**Files:**
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Add flutter_markdown import**

Add at the top of `ai_chat_page.dart`:

```dart
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
```

- [ ] **Step 2: Replace AI message Text with MarkdownBody**

Find the AI message text rendering (after Task 2 modifications):

```dart
if (msg.isThinking)
  const TypingIndicator()
else if (msg.text.isNotEmpty)
  Text(msg.text, style: TextStyle(
    fontSize: 14, color: isUser ? Colors.white : const Color(0xFFc0c0e0))),
```

Replace with:

```dart
if (msg.isThinking)
  const TypingIndicator()
else if (msg.text.isNotEmpty && isUser)
  Text(msg.text, style: const TextStyle(fontSize: 14, color: Colors.white))
else if (msg.text.isNotEmpty && !isUser)
  MarkdownBody(
    data: msg.text,
    styleSheet: MarkdownStyleSheet(
      p: const TextStyle(fontSize: 14, color: Color(0xFFc0c0e0), height: 1.5),
      strong: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white),
      em: const TextStyle(fontStyle: FontStyle.italic, color: Color(0xFFc0c0e0)),
      code: TextStyle(
        fontSize: 13,
        color: const Color(0xFF60a5fa),
        backgroundColor: _card,
        fontFamily: 'monospace',
      ),
      codeblockDecoration: BoxDecoration(
        color: _card,
        borderRadius: BorderRadius.circular(8),
      ),
      blockquote: const TextStyle(color: Color(0xFF9ca3af)),
      listBullet: const TextStyle(color: Color(0xFF60a5fa)),
      a: const TextStyle(color: Color(0xFF60a5fa), decoration: TextDecoration.underline),
      h1: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: Colors.white),
      h2: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.white),
      h3: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white),
    ),
    onTapLink: (text, href, title) {
      if (href != null) {
        launchUrl(Uri.parse(href));
      }
    },
  ),
```

- [ ] **Step 3: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "feat(chat): render AI responses with Markdown formatting"
```

---

### Task 7: Interactive Business Cards

**Files:**
- Create: `smartstay-flutter/lib/widgets/chat_card.dart`
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Create ChatCard widget**

Create `smartstay-flutter/lib/widgets/chat_card.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class ChatCardWidget extends StatelessWidget {
  final Map<String, dynamic> card;
  final bool isStreaming;

  const ChatCardWidget({
    super.key,
    required this.card,
    required this.isStreaming,
  });

  static const _cardBg = Color(0xFF1f2937);

  @override
  Widget build(BuildContext context) {
    final type = card['type'] as String? ?? 'info';
    final title = card['title'] as String? ?? '';
    final isError = type == 'error';

    return GestureDetector(
      onTap: () => _onTap(context, type),
      child: Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: _cardBg,
          borderRadius: BorderRadius.circular(12),
          border: isError
              ? Border.all(color: const Color(0xFFef4444), width: 1)
              : Border.all(color: const Color(0xFF374151), width: 1),
        ),
        child: Row(
          children: [
            _buildIcon(type),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: isError ? const Color(0xFFfca5a5) : Colors.white,
                    ),
                  ),
                  if (_getSubtitle(type) != null) ...[
                    const SizedBox(height: 2),
                    Text(
                      _getSubtitle(type)!,
                      style: const TextStyle(fontSize: 11, color: Color(0xFF9ca3af)),
                    ),
                  ],
                ],
              ),
            ),
            if (_hasNavigation(type))
              const Icon(Icons.chevron_right, color: Color(0xFF6b7280), size: 18),
          ],
        ),
      ),
    );
  }

  Widget _buildIcon(String type) {
    if (isStreaming) {
      return const SizedBox(
        width: 20, height: 20,
        child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF60a5fa)),
      );
    }
    final iconData = switch (type) {
      'workOrder' => Icons.assignment_outlined,
      'deviceControl' => Icons.devices_outlined,
      'pricing' => Icons.attach_money,
      'error' => Icons.error_outline,
      _ => Icons.check_circle_outline,
    };
    final color = switch (type) {
      'error' => const Color(0xFFef4444),
      'workOrder' => const Color(0xFFf59e0b),
      'deviceControl' => const Color(0xFF10b981),
      'pricing' => const Color(0xFF8b5cf6),
      _ => const Color(0xFF60a5fa),
    };
    return Icon(iconData, color: color, size: 20);
  }

  String? _getSubtitle(String type) {
    return switch (type) {
      'workOrder' => '点击查看详情',
      'deviceControl' => '设备已更新',
      'pricing' => '待审批',
      'error' => '请重试或联系前台',
      _ => null,
    };
  }

  bool _hasNavigation(String type) {
    return type == 'workOrder' || type == 'deviceControl';
  }

  void _onTap(BuildContext context, String type) {
    switch (type) {
      case 'workOrder':
        context.go('/work-orders');
        break;
      case 'deviceControl':
        context.go('/room-control');
        break;
    }
  }
}
```

- [ ] **Step 2: Replace card rendering in AIChatPage**

In `ai_chat_page.dart`, add the import:

```dart
import '../../widgets/chat_card.dart';
```

Replace the entire `msg.cards.map(...)` block (the one from Task 3 with BlocBuilder) with:

```dart
...msg.cards.map((card) => BlocBuilder<ChatBloc, ChatState>(
  buildWhen: (prev, curr) => prev.isStreaming != curr.isStreaming,
  builder: (context, state) {
    return ChatCardWidget(
      card: card,
      isStreaming: state.isStreaming,
    );
  },
)),
```

- [ ] **Step 3: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add smartstay-flutter/lib/widgets/chat_card.dart smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "feat(chat): add interactive business cards with navigation"
```

---

### Task 8: Multi-Session History — Backend

**Files:**
- Modify: `backend/app/api/ai.py`

- [ ] **Step 1: Add GET /api/ai/chat/sessions endpoint**

In `backend/app/api/ai.py`, add after the existing `get_chat_history` endpoint:

```python
@router.get("/chat/sessions")
async def get_chat_sessions(
    current_user: Guest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出当前住客的所有聊天会话"""
    result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.order_id.in_(
                select(Order.id).where(Order.user_id == current_user.id)
            )
        )
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()

    out = []
    for s in sessions:
        msg_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == s.id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at)
            .limit(1)
        )
        first_msg = msg_result.scalar_one_or_none()
        out.append({
            "id": str(s.id),
            "created_at": cst_isoformat(s.created_at),
            "first_message": first_msg.content[:30] if first_msg else "",
            "status": s.status,
        })
    return out
```

- [ ] **Step 2: Verify backend compiles**

```bash
cd backend && poetry run python -m py_compile app/api/ai.py
```

Expected: No output (success).

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/ai.py
git commit -m "feat(api): add GET /api/ai/chat/sessions endpoint"
```

---

### Task 9: Multi-Session History — Frontend

**Files:**
- Modify: `smartstay-flutter/lib/blocs/chat/chat_event.dart`
- Modify: `smartstay-flutter/lib/blocs/chat/chat_state.dart`
- Modify: `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`
- Create: `smartstay-flutter/lib/pages/ai_chat/session_list_page.dart`
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Add session events**

In `smartstay-flutter/lib/blocs/chat/chat_event.dart`, add:

```dart
class ChatSessionsLoadRequested {
  const ChatSessionsLoadRequested();
}

class ChatSessionSwitchRequested {
  final String sessionId;
  const ChatSessionSwitchRequested(this.sessionId);
}

class ChatNewSessionRequested {
  const ChatNewSessionRequested();
}
```

- [ ] **Step 2: Add session state fields**

In `smartstay-flutter/lib/blocs/chat/chat_state.dart`, add to `ChatState`:

```dart
class ChatState {
  final List<ChatMessage> messages;
  final bool isStreaming;
  final String? error;
  final List<Map<String, dynamic>> sessions;
  final String? currentSessionId;

  const ChatState({
    this.messages = const [],
    this.isStreaming = false,
    this.error,
    this.sessions = const [],
    this.currentSessionId,
  });

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isStreaming,
    String? error,
    List<Map<String, dynamic>>? sessions,
    String? currentSessionId,
  }) {
    return ChatState(
      messages: messages ?? this.messages,
      isStreaming: isStreaming ?? this.isStreaming,
      error: error,
      sessions: sessions ?? this.sessions,
      currentSessionId: currentSessionId ?? this.currentSessionId,
    );
  }
}
```

- [ ] **Step 3: Implement session handlers in ChatBloc**

In `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`, register the new handlers in the constructor:

```dart
on<ChatSessionsLoadRequested>(_onLoadSessions);
on<ChatSessionSwitchRequested>(_onSwitchSession);
on<ChatNewSessionRequested>(_onNewSession);
```

Add the handler methods:

```dart
Future<void> _onLoadSessions(
  ChatSessionsLoadRequested event,
  Emitter<ChatState> emit,
) async {
  try {
    final resp = await _api.get('/api/ai/chat/sessions');
    final sessions = (resp.data as List).cast<Map<String, dynamic>>();
    emit(state.copyWith(sessions: sessions));
  } catch (_) {}
}

Future<void> _onSwitchSession(
  ChatSessionSwitchRequested event,
  Emitter<ChatState> emit,
) async {
  try {
    final resp = await _api.get('/api/ai/chat/${event.sessionId}/history');
    final history = resp.data as List;
    final messages = history.map((m) => ChatMessage(
      id: m['id'] as String,
      isUser: m['role'] == 'user',
      text: m['content'] as String,
      cards: (m['tool_calls'] as Map<String, dynamic>?)?['cards'] as List<Map<String, dynamic>>? ?? [],
    )).toList();
    emit(ChatState(
      messages: messages,
      currentSessionId: event.sessionId,
      sessions: state.sessions,
    ));
  } catch (_) {}
}

void _onNewSession(ChatNewSessionRequested event, Emitter<ChatState> emit) {
  emit(ChatState(sessions: state.sessions));
}
```

- [ ] **Step 4: Create SessionListPage**

Create `smartstay-flutter/lib/pages/ai_chat/session_list_page.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../blocs/chat/chat_bloc.dart';
import '../../blocs/chat/chat_event.dart';
import '../../blocs/chat/chat_state.dart';

class SessionListPage extends StatelessWidget {
  const SessionListPage({super.key});

  static const _bg = Color(0xFF0a0a1e);
  static const _card = Color(0xFF1f2937);
  static const _blue = Color(0xFF2563eb);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        foregroundColor: Colors.white,
        title: const Text('聊天记录', style: TextStyle(fontSize: 16)),
        actions: [
          TextButton.icon(
            onPressed: () {
              context.read<ChatBloc>().add(const ChatNewSessionRequested());
              Navigator.pop(context);
            },
            icon: const Icon(Icons.add, color: _blue, size: 18),
            label: const Text('新会话', style: TextStyle(color: _blue, fontSize: 13)),
          ),
        ],
      ),
      body: BlocBuilder<ChatBloc, ChatState>(
        buildWhen: (prev, curr) => prev.sessions != curr.sessions,
        builder: (context, state) {
          if (state.sessions.isEmpty) {
            return const Center(
              child: Text('暂无聊天记录', style: TextStyle(color: Color(0xFF9ca3af), fontSize: 14)),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: state.sessions.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, idx) {
              final session = state.sessions[idx];
              final isActive = session['id'] == state.currentSessionId;
              return GestureDetector(
                onTap: () {
                  context.read<ChatBloc>().add(
                    ChatSessionSwitchRequested(session['id'] as String),
                  );
                  Navigator.pop(context);
                },
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isActive ? _blue.withOpacity(0.15) : _card,
                    borderRadius: BorderRadius.circular(12),
                    border: isActive
                        ? Border.all(color: _blue.withOpacity(0.5))
                        : null,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        session['first_message'] as String? ?? '新对话',
                        style: const TextStyle(fontSize: 14, color: Colors.white),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        session['created_at'] as String? ?? '',
                        style: const TextStyle(fontSize: 11, color: Color(0xFF6b7280)),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
```

- [ ] **Step 5: Add history button to AIChatPage header**

In `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`, add the import:

```dart
import 'session_list_page.dart';
```

In the header `Row`, replace `const SizedBox(width: 24)` (the one on the right side) with:

```dart
GestureDetector(
  onTap: () {
    context.read<ChatBloc>().add(const ChatSessionsLoadRequested());
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => BlocProvider.value(
        value: context.read<ChatBloc>(),
        child: const SessionListPage(),
      ),
    );
  },
  child: const Icon(Icons.history_rounded, color: Color(0xFF9ca3af), size: 22),
),
```

- [ ] **Step 6: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add smartstay-flutter/lib/blocs/chat/ smartstay-flutter/lib/pages/ai_chat/ smartstay-flutter/lib/widgets/
git commit -m "feat(chat): add multi-session history with session list"
```

---

**Phase 2 complete. Run full verification:**

```bash
cd smartstay-flutter && flutter analyze
cd backend && poetry run python -m py_compile app/api/ai.py
```

Expected: No errors.

---

## Phase 3: Code Refactoring

### Task 10: Type-Safe ChatCard Model

**Files:**
- Create: `smartstay-flutter/lib/models/chat_card.dart`
- Modify: `smartstay-flutter/lib/blocs/chat/chat_state.dart`
- Modify: `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`
- Modify: `smartstay-flutter/lib/widgets/chat_card.dart`
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: Create ChatCard model**

Create `smartstay-flutter/lib/models/chat_card.dart`:

```dart
enum ChatCardType { success, error, deviceControl, workOrder, pricing, info }

class ChatCard {
  final ChatCardType type;
  final String title;
  final String? subtitle;
  final Map<String, dynamic>? metadata;

  const ChatCard({
    required this.type,
    required this.title,
    this.subtitle,
    this.metadata,
  });

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

  Map<String, dynamic> toJson() {
    return {
      'type': type.name,
      'title': title,
      if (subtitle != null) 'subtitle': subtitle,
      if (metadata != null) ...metadata!,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ChatCard && type == other.type && title == other.title;

  @override
  int get hashCode => type.hashCode ^ title.hashCode;
}
```

- [ ] **Step 2: Update ChatMessage to use ChatCard**

In `smartstay-flutter/lib/blocs/chat/chat_state.dart`, add import and change the `cards` type:

```dart
import '../models/chat_card.dart';

class ChatMessage {
  final String id;
  final bool isUser;
  final String text;
  final List<ChatCard> cards;
  final bool isThinking;

  const ChatMessage({
    required this.id,
    required this.isUser,
    this.text = '',
    this.cards = const [],
    this.isThinking = false,
  });
}
```

- [ ] **Step 3: Update ChatBloc to use ChatCard.fromJson**

In `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`, add import:

```dart
import '../../models/chat_card.dart';
```

Replace all occurrences of:
```dart
cards.add(data['card'] as Map<String, dynamic>);
```
with:
```dart
cards.add(ChatCard.fromJson(data['card'] as Map<String, dynamic>));
```

Replace all `List<Map<String, dynamic>> cards` declarations with `List<ChatCard> cards`.

Replace all `List.from(cards)` with `List<ChatCard>.from(cards)`.

- [ ] **Step 4: Update ChatCardWidget to accept ChatCard**

In `smartstay-flutter/lib/widgets/chat_card.dart`, change the `card` parameter type:

```dart
import '../models/chat_card.dart';

class ChatCardWidget extends StatelessWidget {
  final ChatCard card;
  final bool isStreaming;

  const ChatCardWidget({
    super.key,
    required this.card,
    required this.isStreaming,
  });

  // ... rest stays the same, but update references:
  // card['type'] → card.type.name
  // card['title'] → card.title
```

Update the build method to use `card.type.name` instead of `card['type']` and `card.title` instead of `card['title']`.

- [ ] **Step 5: Update AIChatPage card mapping**

In `ai_chat_page.dart`, the `msg.cards.map(...)` already passes `card` to `ChatCardWidget`. No change needed since the type now matches.

- [ ] **Step 6: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add smartstay-flutter/lib/models/chat_card.dart smartstay-flutter/lib/blocs/chat/ smartstay-flutter/lib/widgets/chat_card.dart smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "refactor(chat): replace Map<String, dynamic> cards with typed ChatCard model"
```

---

### Task 11: Extract SSE Stream Handler

**Files:**
- Create: `smartstay-flutter/lib/core/sse_stream_handler.dart`
- Modify: `smartstay-flutter/lib/core/sse_parser.dart` (keep for backward compat, or delete if unused elsewhere)

- [ ] **Step 1: Create SSEStreamHandler**

Create `smartstay-flutter/lib/core/sse_stream_handler.dart`:

```dart
import 'dart:async';
import 'dart:convert';

import '../models/chat_card.dart';

sealed class ChatStreamEvent {}

class ChatStreamText extends ChatStreamEvent {
  final String content;
  ChatStreamText(this.content);
}

class ChatStreamCard extends ChatStreamEvent {
  final ChatCard card;
  ChatStreamCard(this.card);
}

class ChatStreamDone extends ChatStreamEvent {}

class ChatStreamError extends ChatStreamEvent {
  final String message;
  ChatStreamError(this.message);
}

class SSEStreamHandler {
  final _controller = StreamController<ChatStreamEvent>.broadcast();
  String _buffer = '';
  int _failCount = 0;

  Stream<ChatStreamEvent> get stream => _controller.stream;

  void addChunk(String chunk) {
    _buffer += chunk;

    while (_buffer.contains('\n')) {
      final idx = _buffer.indexOf('\n');
      final line = _buffer.substring(0, idx).trim();
      _buffer = _buffer.substring(idx + 1);

      if (line.isEmpty) continue;
      if (!line.startsWith('data: ')) continue;

      final jsonStr = line.substring(6);
      try {
        _failCount = 0;
        final data = jsonDecode(jsonStr) as Map<String, dynamic>;
        final type = data['type'] as String?;

        if (type == 'text') {
          final content = (data['content'] ?? '').toString();
          _controller.add(ChatStreamText(content));
        } else if (type == 'card') {
          final cardData = data['card'] as Map<String, dynamic>;
          _controller.add(ChatStreamCard(ChatCard.fromJson(cardData)));
        } else if (type == 'done') {
          _controller.add(ChatStreamDone());
          return;
        }
      } catch (_) {
        _failCount++;
        if (_failCount >= 10) {
          _failCount = 0;
          continue;
        } else {
          _buffer = line + '\n' + _buffer;
          break;
        }
      }
    }
  }

  void addError(String message) {
    _controller.add(ChatStreamError(message));
  }

  void close() {
    _controller.close();
  }
}
```

- [ ] **Step 2: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors (new file, not yet wired up).

- [ ] **Step 3: Commit**

```bash
git add smartstay-flutter/lib/core/sse_stream_handler.dart
git commit -m "refactor(chat): add SSEStreamHandler with typed events"
```

---

### Task 12: ChatStreamService + ChatBloc Refactor

**Files:**
- Create: `smartstay-flutter/lib/services/chat_stream_service.dart`
- Modify: `smartstay-flutter/lib/blocs/chat/chat_bloc.dart`

- [ ] **Step 1: Create ChatStreamService**

Create `smartstay-flutter/lib/services/chat_stream_service.dart`:

```dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import '../core/api_client.dart';
import '../core/sse_stream_handler.dart';
import '../models/chat_card.dart';

import '../blocs/chat/html_stub.dart' if (dart.library.html) 'dart:html' as html;

class ChatStreamService {
  final _api = ApiClient();
  http.Client? _httpClient;
  html.HttpRequest? _webRequest;

  Stream<ChatStreamEvent> sendMessage(String message) async* {
    final handler = SSEStreamHandler();

    if (kIsWeb) {
      yield* _sendViaWeb(message, handler);
    } else {
      yield* _sendViaNative(message, handler);
    }
  }

  Stream<ChatStreamEvent> _sendViaNative(String message, SSEStreamHandler handler) async* {
    final uri = Uri.parse('${_api.dio.options.baseUrl}/api/ai/chat');
    final request = http.Request('POST', uri);
    request.headers['Content-Type'] = 'application/json';
    final token = _api.accessToken;
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    request.body = jsonEncode({'message': message});

    final client = http.Client();
    _httpClient = client;

    try {
      final streamedResponse = await client.send(request);

      if (streamedResponse.statusCode == 401) {
        handler.addError('auth_expired');
        yield* handler.stream;
        return;
      }

      final sub = streamedResponse.stream
          .transform(const Utf8Decoder())
          .listen(
            handler.addChunk,
            onError: (_) => handler.addError('连接中断'),
            onDone: () => handler.close(),
          );

      yield* handler.stream;
      await sub.asFuture<void>().catchError((_) {});
    } catch (_) {
      handler.addError('发送失败');
      yield* handler.stream;
    } finally {
      client.close();
      _httpClient = null;
    }
  }

  Stream<ChatStreamEvent> _sendViaWeb(String message, SSEStreamHandler handler) async* {
    final completer = Completer<void>();
    final token = _api.accessToken;

    final request = html.HttpRequest();
    _webRequest = request;

    request.open('POST', '${_api.dio.options.baseUrl}/api/ai/chat');
    request.setRequestHeader('Content-Type', 'application/json');
    if (token != null) {
      request.setRequestHeader('Authorization', 'Bearer $token');
    }
    request.responseType = 'text';

    int lastPos = 0;

    request.onProgress.listen((_) {
      final fullText = request.responseText ?? '';
      if (fullText.length > lastPos) {
        handler.addChunk(fullText.substring(lastPos));
        lastPos = fullText.length;
      }
    });

    request.onLoad.listen((_) {
      if (!completer.isCompleted) {
        if (request.status == 401) {
          handler.addError('auth_expired');
          completer.complete();
          return;
        }
        final fullText = request.responseText ?? '';
        if (fullText.length > lastPos) {
          handler.addChunk(fullText.substring(lastPos));
        }
        handler.close();
        completer.complete();
      }
    });

    request.onError.listen((_) {
      if (!completer.isCompleted) {
        handler.addError('连接中断');
        completer.complete();
      }
    });

    request.send(jsonEncode({'message': message}));

    yield* handler.stream;
    await completer.future;
    _webRequest = null;
  }

  void cancel() {
    _httpClient?.close();
    _httpClient = null;
    _webRequest?.abort();
    _webRequest = null;
  }
}
```

- [ ] **Step 2: Refactor ChatBloc to use ChatStreamService**

Replace the entire `smartstay-flutter/lib/blocs/chat/chat_bloc.dart` with:

```dart
import 'dart:async';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../core/api_client.dart';
import '../../core/sse_stream_handler.dart';
import '../../models/chat_card.dart';
import '../../services/chat_stream_service.dart';
import 'chat_event.dart';
import 'chat_state.dart';

class ChatBloc extends Bloc<Object, ChatState> {
  ChatBloc() : super(const ChatState()) {
    on<ChatMessageSent>(_onSend);
    on<ChatStreamCancelled>(_onCancel);
    on<ChatSessionsLoadRequested>(_onLoadSessions);
    on<ChatSessionSwitchRequested>(_onSwitchSession);
    on<ChatNewSessionRequested>(_onNewSession);
  }

  final _api = ApiClient();
  final _streamService = ChatStreamService();

  Future<void> _onSend(ChatMessageSent event, Emitter<ChatState> emit) async {
    final userMsg = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      isUser: true,
      text: event.message,
    );
    final aiMsgId = 'ai_${DateTime.now().millisecondsSinceEpoch}';

    final messages = [
      ...state.messages,
      userMsg,
      ChatMessage(id: aiMsgId, isUser: false, isThinking: true),
    ];
    emit(ChatState(
      messages: messages,
      isStreaming: true,
      sessions: state.sessions,
      currentSessionId: state.currentSessionId,
    ));

    final cards = <ChatCard>[];
    var retried = false;

    await for (final event in _streamService.sendMessage(event.message)) {
      if (event is ChatStreamText) {
        final idx = state.messages.indexWhere((m) => m.id == aiMsgId);
        if (idx == -1) continue;
        final msgs = List<ChatMessage>.from(state.messages);
        msgs[idx] = ChatMessage(
          id: aiMsgId,
          isUser: false,
          text: msgs[idx].text + event.content,
          cards: List<ChatCard>.from(cards),
          isThinking: false,
        );
        emit(ChatState(
          messages: msgs,
          isStreaming: true,
          sessions: state.sessions,
          currentSessionId: state.currentSessionId,
        ));
      } else if (event is ChatStreamCard) {
        cards.add(event.card);
        final idx = state.messages.indexWhere((m) => m.id == aiMsgId);
        if (idx == -1) continue;
        final msgs = List<ChatMessage>.from(state.messages);
        msgs[idx] = ChatMessage(
          id: aiMsgId,
          isUser: false,
          text: msgs[idx].text,
          cards: List<ChatCard>.from(cards),
          isThinking: false,
        );
        emit(ChatState(
          messages: msgs,
          isStreaming: true,
          sessions: state.sessions,
          currentSessionId: state.currentSessionId,
        ));
      } else if (event is ChatStreamDone) {
        final idx = state.messages.indexWhere((m) => m.id == aiMsgId);
        if (idx != -1) {
          final msgs = List<ChatMessage>.from(state.messages);
          msgs[idx] = ChatMessage(
            id: aiMsgId,
            isUser: false,
            text: msgs[idx].text,
            cards: List<ChatCard>.from(cards),
          );
          emit(ChatState(
            messages: msgs,
            isStreaming: false,
            sessions: state.sessions,
            currentSessionId: state.currentSessionId,
          ));
        }
      } else if (event is ChatStreamError) {
        if (event.message == 'auth_expired' && !retried) {
          retried = true;
          try {
            await _api.refreshAccessToken();
            await for (final retryEvent in _streamService.sendMessage(event.message)) {
              // Process retry events same as above (simplified)
              if (retryEvent is ChatStreamText) {
                final idx = state.messages.indexWhere((m) => m.id == aiMsgId);
                if (idx == -1) continue;
                final msgs = List<ChatMessage>.from(state.messages);
                msgs[idx] = ChatMessage(
                  id: aiMsgId, isUser: false,
                  text: msgs[idx].text + retryEvent.content,
                  cards: List<ChatCard>.from(cards),
                  isThinking: false,
                );
                emit(ChatState(
                  messages: msgs, isStreaming: true,
                  sessions: state.sessions, currentSessionId: state.currentSessionId,
                ));
              } else if (retryEvent is ChatStreamCard) {
                cards.add(retryEvent.card);
              } else if (retryEvent is ChatStreamDone) {
                final idx = state.messages.indexWhere((m) => m.id == aiMsgId);
                if (idx != -1) {
                  final msgs = List<ChatMessage>.from(state.messages);
                  msgs[idx] = ChatMessage(
                    id: aiMsgId, isUser: false,
                    text: msgs[idx].text, cards: List<ChatCard>.from(cards),
                  );
                  emit(ChatState(
                    messages: msgs, isStreaming: false,
                    sessions: state.sessions, currentSessionId: state.currentSessionId,
                  ));
                }
              } else if (retryEvent is ChatStreamError) {
                emit(state.copyWith(isStreaming: false, error: '登录已过期，请重新登录'));
                return;
              }
            }
          } catch (_) {
            emit(state.copyWith(isStreaming: false, error: '登录已过期，请重新登录'));
            return;
          }
        } else {
          emit(state.copyWith(isStreaming: false, error: event.message));
          return;
        }
      }
    }

    if (state.isStreaming) {
      emit(state.copyWith(isStreaming: false));
    }
  }

  void _onCancel(ChatStreamCancelled event, Emitter<ChatState> emit) {
    _streamService.cancel();
    emit(state.copyWith(isStreaming: false));
  }

  Future<void> _onLoadSessions(
    ChatSessionsLoadRequested event,
    Emitter<ChatState> emit,
  ) async {
    try {
      final resp = await _api.get('/api/ai/chat/sessions');
      final sessions = (resp.data as List).cast<Map<String, dynamic>>();
      emit(state.copyWith(sessions: sessions));
    } catch (_) {}
  }

  Future<void> _onSwitchSession(
    ChatSessionSwitchRequested event,
    Emitter<ChatState> emit,
  ) async {
    try {
      final resp = await _api.get('/api/ai/chat/${event.sessionId}/history');
      final history = resp.data as List;
      final messages = history.map((m) => ChatMessage(
        id: m['id'] as String,
        isUser: m['role'] == 'user',
        text: m['content'] as String,
        cards: ((m['tool_calls'] as Map<String, dynamic>?)?['cards'] as List?)
                ?.map((c) => ChatCard.fromJson(c as Map<String, dynamic>))
                .toList() ?? [],
      )).toList();
      emit(ChatState(
        messages: messages,
        currentSessionId: event.sessionId,
        sessions: state.sessions,
      ));
    } catch (_) {}
  }

  void _onNewSession(ChatNewSessionRequested event, Emitter<ChatState> emit) {
    emit(ChatState(sessions: state.sessions));
  }

  @override
  Future<void> close() {
    _streamService.cancel();
    return super.close();
  }
}
```

- [ ] **Step 3: Verify**

```bash
cd smartstay-flutter && flutter analyze
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add smartstay-flutter/lib/services/chat_stream_service.dart smartstay-flutter/lib/blocs/chat/chat_bloc.dart
git commit -m "refactor(chat): extract ChatStreamService, simplify ChatBloc to state management only"
```

---

**Phase 3 complete. Final verification:**

```bash
cd smartstay-flutter && flutter analyze
cd backend && poetry run python -m py_compile app/api/ai.py
```

Expected: No errors across all three phases.

---

## Summary

| Phase | Tasks | Files Changed | User-Visible |
|-------|-------|--------------|--------------|
| 1. UX Optimization | 4 | 6 | Stop button, typing indicator, tool status, quick chips |
| 2. Feature Enhancement | 5 | 8 | Markdown, interactive cards, voice input*, multi-session history |
| 3. Code Refactoring | 3 | 5 | None (internal improvement) |
| **Total** | **12** | **~14 unique** | |

*Voice input (spec 2.3) is described in the spec but deferred to a follow-up plan due to complexity of阿里云 ASR integration. The infrastructure (record + permission_handler deps) is in place.
