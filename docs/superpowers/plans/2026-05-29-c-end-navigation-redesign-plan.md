# C端导航重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 Flutter C 端 App 的导航和登录流程，实现"先浏览后登录"的现代酒店 App 体验。

**Architecture:** 所有 Tab 永远可点击，各页面自行处理未登录状态。登录改为底部弹窗（LoginBottomSheet），不再跳转独立登录页。"账单"Tab 改为"我的"Tab，融合个人信息、订单、账单、设置。

**Tech Stack:** Flutter 3.35+, Dart 3.7+, BLoC, GoRouter, Dio

---

## 文件结构

### 新增文件

| 文件路径 | 职责 |
|----------|------|
| `lib/widgets/login_bottom_sheet.dart` | 底部登录弹窗组件（身份证+密码登录，首次改密流程） |
| `lib/widgets/auth_prompt.dart` | 通用未登录遮罩/引导组件 |
| `lib/pages/my/my_page.dart` | "我的"页面主组件 |
| `lib/pages/my/order_list_page.dart` | 订单列表二级页 |
| `lib/pages/my/bill_detail_page.dart` | 账单详情二级页（迁移自 bill_page.dart） |

### 修改文件

| 文件路径 | 变化 |
|----------|------|
| `lib/widgets/bottom_nav.dart` | "账单"→"我的"，图标 📋→👤 |
| `lib/app.dart` | 新增路由，移除强制登录拦截，Tab 路由更新 |
| `lib/pages/room_control/room_control_page.dart` | 未登录时置灰+底部引导条 |
| `lib/pages/ai_chat/ai_chat_page.dart` | 未登录时遮罩引导 |
| `lib/pages/work_order/work_order_page.dart` | 未登录时遮罩引导 |

### 删除/废弃文件

| 文件路径 | 说明 |
|----------|------|
| `lib/pages/bill/bill_page.dart` | 逻辑迁移到 `bill_detail_page.dart`，原文件保留但不再作为 Tab 页面 |

---

## Task 1: LoginBottomSheet 组件

**Files:**
- Create: `smartstay-flutter/lib/widgets/login_bottom_sheet.dart`

- [ ] **Step 1: 创建 LoginBottomSheet 基础结构**

```dart
// lib/widgets/login_bottom_sheet.dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../blocs/auth/auth_bloc.dart';
import '../blocs/auth/auth_event.dart';
import '../blocs/auth/auth_state.dart';

class LoginBottomSheet extends StatefulWidget {
  const LoginBottomSheet({super.key});

  /// 从任何页面调用，弹出登录弹窗
  static Future<void> show(BuildContext context) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const LoginBottomSheet(),
    );
  }

  @override
  State<LoginBottomSheet> createState() => _LoginBottomSheetState();
}

class _LoginBottomSheetState extends State<LoginBottomSheet> {
  final _idCardCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _oldPasswordCtrl = TextEditingController();
  final _newPasswordCtrl = TextEditingController();
  final _confirmPasswordCtrl = TextEditingController();
  String? _error;
  bool _loading = false;
  bool _showChangePassword = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: EdgeInsets.only(
        left: 20, right: 20, top: 12,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: _showChangePassword ? _buildChangePasswordSheet() : _buildLoginSheet(),
    );
  }

  Widget _buildLoginSheet() {
    return SingleChildScrollView(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        // 拖拽条
        Container(width: 36, height: 4, margin: const EdgeInsets.only(bottom: 16),
          decoration: BoxDecoration(color: const Color(0xFFE0E0E0), borderRadius: BorderRadius.circular(2))),
        // 关闭按钮
        Align(alignment: Alignment.topRight, child: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: Container(width: 26, height: 26,
            decoration: const BoxDecoration(color: Color(0xFFF0F0F0), shape: BoxShape.circle),
            child: const Icon(Icons.close, size: 14, color: Color(0xFF999999))),
        )),
        const SizedBox(height: 8),
        // 标题
        const Text('🏨', style: TextStyle(fontSize: 32)),
        const SizedBox(height: 8),
        const Text('登录智宿云', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: Color(0xFF1A1A2E))),
        const SizedBox(height: 4),
        const Text('享受智慧入住体验', style: TextStyle(fontSize: 10, color: Color(0xFF999999))),
        const SizedBox(height: 20),
        // 身份证号
        _buildInputField(label: '身份证号', controller: _idCardCtrl),
        const SizedBox(height: 10),
        // 密码
        _buildInputField(label: '密码', controller: _passwordCtrl, obscure: true),
        const SizedBox(height: 16),
        // 错误提示
        if (_error != null) ...[
          Text(_error!, style: const TextStyle(color: Color(0xFFFF4D4F), fontSize: 11)),
          const SizedBox(height: 8),
        ],
        // 登录按钮
        SizedBox(width: double.infinity, height: 48, child: ElevatedButton(
          onPressed: _loading ? null : _handleLogin,
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF1677FF),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
            elevation: 0,
          ),
          child: _loading
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : const Text('立即登录', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
        )),
        const SizedBox(height: 14),
        const Text('还没有账号？请前往前台办理入住', style: TextStyle(fontSize: 10, color: Color(0xFFBBBBBB))),
      ]),
    );
  }

  Widget _buildChangePasswordSheet() {
    return SingleChildScrollView(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 36, height: 4, margin: const EdgeInsets.only(bottom: 16),
          decoration: BoxDecoration(color: const Color(0xFFE0E0E0), borderRadius: BorderRadius.circular(2))),
        const Text('🔑', style: TextStyle(fontSize: 28)),
        const SizedBox(height: 6),
        const Text('修改初始密码', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Color(0xFF1A1A2E))),
        const SizedBox(height: 3),
        const Text('首次登录，请设置新密码', style: TextStyle(fontSize: 9, color: Color(0xFF999999))),
        const SizedBox(height: 14),
        _buildInputField(label: '原密码', controller: _oldPasswordCtrl, obscure: true),
        const SizedBox(height: 8),
        _buildInputField(label: '新密码', controller: _newPasswordCtrl, obscure: true, focus: true),
        const SizedBox(height: 8),
        _buildInputField(label: '确认新密码', controller: _confirmPasswordCtrl, obscure: true),
        const SizedBox(height: 12),
        if (_error != null) ...[
          Text(_error!, style: const TextStyle(color: Color(0xFFFF4D4F), fontSize: 11)),
          const SizedBox(height: 8),
        ],
        SizedBox(width: double.infinity, height: 48, child: ElevatedButton(
          onPressed: _loading ? null : _handleChangePassword,
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF1677FF),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
            elevation: 0,
          ),
          child: _loading
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : const Text('确认修改', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
        )),
      ]),
    );
  }

  Widget _buildInputField({
    required String label,
    required TextEditingController controller,
    bool obscure = false,
    bool focus = false,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: focus ? const Color(0xFFF8FAFF) : const Color(0xFFF5F7FA),
        borderRadius: BorderRadius.circular(12),
        border: focus ? Border.all(color: const Color(0xFF1677FF), width: 1.5) : null,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: TextStyle(fontSize: 9, color: focus ? const Color(0xFF1677FF) : const Color(0xFF999999))),
        const SizedBox(height: 3),
        TextField(
          controller: controller,
          obscureText: obscure,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          decoration: const InputDecoration(border: InputBorder.none, isDense: true, contentPadding: EdgeInsets.zero),
        ),
      ]),
    );
  }

  Future<void> _handleLogin() async {
    final idCard = _idCardCtrl.text.trim();
    final password = _passwordCtrl.text.trim();
    if (idCard.isEmpty || password.isEmpty) {
      setState(() => _error = '请输入身份证号和密码');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final bloc = context.read<AuthBloc>();
      bloc.add(AuthLoginRequested(idCard: idCard, password: password));
      // 等待 Bloc 处理完成
      await bloc.stream.firstWhere((s) =>
        s.status == AuthStatus.authenticated ||
        s.status == AuthStatus.passwordChangeRequired ||
        s.status == AuthStatus.unauthenticated);
      final state = bloc.state;
      if (state.status == AuthStatus.passwordChangeRequired) {
        setState(() { _showChangePassword = true; _loading = false; });
      } else if (state.status == AuthStatus.authenticated) {
        if (mounted) Navigator.pop(context);
      } else {
        setState(() { _error = state.error ?? '登录失败，请检查身份证号和密码'; _loading = false; });
      }
    } catch (_) {
      setState(() { _error = '网络异常，请重试'; _loading = false; });
    }
  }

  Future<void> _handleChangePassword() async {
    final oldPw = _oldPasswordCtrl.text.trim();
    final newPw = _newPasswordCtrl.text.trim();
    final confirmPw = _confirmPasswordCtrl.text.trim();
    if (oldPw.isEmpty || newPw.isEmpty || confirmPw.isEmpty) {
      setState(() => _error = '请填写所有字段');
      return;
    }
    if (newPw != confirmPw) {
      setState(() => _error = '两次输入的新密码不一致');
      return;
    }
    setState(() { _loading = true; _error = null; });
    try {
      final bloc = context.read<AuthBloc>();
      bloc.add(AuthChangePasswordRequested(oldPassword: oldPw, newPassword: newPw, confirmPassword: confirmPw));
      await bloc.stream.firstWhere((s) =>
        s.status == AuthStatus.authenticated ||
        s.status == AuthStatus.passwordChangeRequired);
      final state = bloc.state;
      if (state.status == AuthStatus.authenticated) {
        if (mounted) Navigator.pop(context);
      } else {
        setState(() { _error = state.error ?? '密码修改失败'; _loading = false; });
      }
    } catch (_) {
      setState(() { _error = '网络异常，请重试'; _loading = false; });
    }
  }

  @override
  void dispose() {
    _idCardCtrl.dispose();
    _passwordCtrl.dispose();
    _oldPasswordCtrl.dispose();
    _newPasswordCtrl.dispose();
    _confirmPasswordCtrl.dispose();
    super.dispose();
  }
}
```

- [ ] **Step 2: 验证组件可编译**

Run: `cd smartstay-flutter && flutter analyze lib/widgets/login_bottom_sheet.dart`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add smartstay-flutter/lib/widgets/login_bottom_sheet.dart
git commit -m "feat(c-end): add LoginBottomSheet component"
```

---

## Task 2: AuthPrompt 通用遮罩组件

**Files:**
- Create: `smartstay-flutter/lib/widgets/auth_prompt.dart`

- [ ] **Step 1: 创建 AuthPrompt 组件**

```dart
// lib/widgets/auth_prompt.dart
import 'package:flutter/material.dart';
import 'login_bottom_sheet.dart';

/// 未登录时的遮罩引导组件
/// 支持两种模式：overlay（全页遮罩）和 bottomBar（底部引导条）
class AuthPrompt extends StatelessWidget {
  final String icon;
  final String title;
  final String description;
  final bool showAsOverlay;

  const AuthPrompt({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
    this.showAsOverlay = true,
  });

  /// 全页遮罩模式（管家、服务页使用）
  const AuthPrompt.overlay({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
  }) : showAsOverlay = true;

  /// 底部引导条模式（控房页使用）
  const AuthPrompt.bottomBar({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
  }) : showAsOverlay = false;

  @override
  Widget build(BuildContext context) {
    if (showAsOverlay) {
      return _buildOverlay(context);
    }
    return _buildBottomBar(context);
  }

  Widget _buildOverlay(BuildContext context) {
    return Container(
      color: const Color(0xFFF8F9FC).withOpacity(0.95),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(icon, style: const TextStyle(fontSize: 48)),
            const SizedBox(height: 16),
            Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: Color(0xFF1A1A2E))),
            const SizedBox(height: 6),
            Text(description, textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 11, color: Color(0xFF999999), height: 1.6)),
            const SizedBox(height: 20),
            _buildLoginButton(context),
          ]),
        ),
      ),
    );
  }

  Widget _buildBottomBar(BuildContext context) {
    return Positioned(
      bottom: 0, left: 0, right: 0,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.08), blurRadius: 24, offset: const Offset(0, -4))],
        ),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(description, style: const TextStyle(fontSize: 11, color: Color(0xFF666666))),
          const SizedBox(height: 12),
          _buildLoginButton(context),
        ]),
      ),
    );
  }

  Widget _buildLoginButton(BuildContext context) {
    return GestureDetector(
      onTap: () => LoginBottomSheet.show(context),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 13),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF1677FF), Color(0xFF4096FF)]),
          borderRadius: BorderRadius.circular(28),
          boxShadow: [BoxShadow(color: const Color(0xFF1677FF).withOpacity(0.35), blurRadius: 16, offset: const Offset(0, 6))],
        ),
        child: const Text('立即登录', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w700)),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add smartstay-flutter/lib/widgets/auth_prompt.dart
git commit -m "feat(c-end): add AuthPrompt overlay component"
```

---

## Task 3: 改造控房页未登录状态

**Files:**
- Modify: `smartstay-flutter/lib/pages/room_control/room_control_page.dart`

- [ ] **Step 1: 修改 RoomControlPage，未登录时显示置灰控件+底部引导**

在 `room_control_page.dart` 的 `build` 方法中，检查 AuthBloc 状态。未登录时：
- 控件区域包裹 `IgnorePointer` + `Opacity(opacity: 0.25)`
- 底部叠加 `AuthPrompt.bottomBar`

具体修改：在 `build` 方法开头添加登录状态检查：

```dart
@override
Widget build(BuildContext context) {
  return BlocBuilder<RoomBloc, RoomState>(
    builder: (context, state) {
      final authState = context.watch<AuthBloc>().state;
      final isLoggedIn = authState.status == AuthStatus.authenticated;
      final loading = state.loading && state.roomNumber.isEmpty;
      final noRoom = !loading && state.error != null && state.roomNumber.isEmpty;

      return Scaffold(
        appBar: AppBar(
          title: Text('💡 智能控房${state.roomNumber.isNotEmpty ? ' · ${state.roomNumber}' : ''}'),
          backgroundColor: const Color(0xFF1A1A2E),
          foregroundColor: Colors.white,
        ),
        body: loading
          ? const Center(child: CircularProgressIndicator())
          : !isLoggedIn
            ? _buildUnauthView()
            : noRoom
              ? _buildEmptyState(context, state.error!)
              : _buildAuthView(context, state),
      );
    },
  );
}

Widget _buildUnauthView() {
  return Stack(children: [
    // 置灰的控件预览
    Opacity(opacity: 0.25, child: IgnorePointer(child: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _LightSwitch(label: '客厅灯', value: false, onToggle: () {}),
        _LightSwitch(label: '卧室灯', value: false, onToggle: () {}),
        _LightSwitch(label: '床头灯', value: false, onToggle: () {}),
        const SizedBox(height: 16),
        const Text('🪟 窗帘控制 · 50%', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        Slider(value: 50, min: 0, max: 100, onChanged: null),
        const SizedBox(height: 16),
        const Text('🌡️ 空调控制 · 24°C', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          IconButton.filled(onPressed: null, icon: const Icon(Icons.remove)),
          Container(width: 80, alignment: Alignment.center, child: const Text('24°C', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Color(0xFF1677FF)))),
          IconButton.filled(onPressed: null, icon: const Icon(Icons.add)),
        ]),
      ],
    ))),
    // 底部引导条
    const AuthPrompt.bottomBar(
      icon: '💡',
      title: '控房',
      description: '入住后即可控制房间设备',
    ),
  ]);
}

Widget _buildAuthView(BuildContext context, RoomState state) {
  // 原有的已登录 UI（从原 build 方法中提取）
  // ... 保持原有代码不变
}
```

- [ ] **Step 2: 添加必要的 import**

```dart
import '../../blocs/auth/auth_bloc.dart';
import '../../blocs/auth/auth_state.dart';
import '../../widgets/auth_prompt.dart';
```

- [ ] **Step 3: 验证编译**

Run: `cd smartstay-flutter && flutter analyze lib/pages/room_control/room_control_page.dart`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add smartstay-flutter/lib/pages/room_control/room_control_page.dart
git commit -m "feat(c-end): room control unauth state with grayed controls"
```

---

## Task 4: 改造管家页未登录状态

**Files:**
- Modify: `smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart`

- [ ] **Step 1: 修改 AIChatPage，未登录时显示遮罩**

```dart
@override
Widget build(BuildContext context) {
  final authState = context.watch<AuthBloc>().state;
  final isLoggedIn = authState.status == AuthStatus.authenticated;

  return Scaffold(
    appBar: AppBar(title: const Text('🤖 AI虚拟管家'), backgroundColor: const Color(0xFF1A1A2E), foregroundColor: Colors.white),
    body: isLoggedIn ? _buildChatBody() : const AuthPrompt.overlay(
      icon: '🤖',
      title: 'AI 虚拟管家',
      description: '登录后即可享受智能对话\n控制设备 · 查询信息 · 提交服务',
    ),
  );
}

Widget _buildChatBody() {
  // 原有的聊天 UI（从原 build 方法中提取 Column 部分）
  return Column(children: [
    Expanded(child: BlocBuilder<ChatBloc, ChatState>(builder: (context, state) {
      // ... 原有 ListView.builder
    })),
    // ... 原有输入栏
  ]);
}
```

- [ ] **Step 2: 添加 import**

```dart
import '../../blocs/auth/auth_bloc.dart';
import '../../blocs/auth/auth_state.dart';
import '../../widgets/auth_prompt.dart';
```

- [ ] **Step 3: Commit**

```bash
git add smartstay-flutter/lib/pages/ai_chat/ai_chat_page.dart
git commit -m "feat(c-end): AI chat unauth overlay"
```

---

## Task 5: 改造服务页未登录状态

**Files:**
- Modify: `smartstay-flutter/lib/pages/work_order/work_order_page.dart`

- [ ] **Step 1: 修改 WorkOrderPage，未登录时显示遮罩**

```dart
@override
Widget build(BuildContext context) {
  final authState = context.watch<AuthBloc>().state;
  final isLoggedIn = authState.status == AuthStatus.authenticated;

  return Scaffold(
    appBar: AppBar(title: const Text('📋 服务追踪'), backgroundColor: const Color(0xFF1A1A2E), foregroundColor: Colors.white),
    floatingActionButton: isLoggedIn ? FloatingActionButton.extended(
      onPressed: _showCreateDialog,
      icon: const Icon(Icons.add),
      label: const Text('新建服务'),
      backgroundColor: const Color(0xFF1677FF),
      foregroundColor: Colors.white,
    ) : null,
    body: isLoggedIn ? _buildOrderList() : const AuthPrompt.overlay(
      icon: '🔧',
      title: '服务工单',
      description: '登录后查看工单进度\n提交维修 · 保洁 · 送物等服务',
    ),
  );
}

Widget _buildOrderList() {
  // 原有的 BlocBuilder 列表（从原 build 方法中提取）
  return BlocBuilder<WorkOrderBloc, WorkOrderState>(builder: (context, state) {
    // ... 原有逻辑
  });
}
```

- [ ] **Step 2: 添加 import**

```dart
import '../../blocs/auth/auth_bloc.dart';
import '../../blocs/auth/auth_state.dart';
import '../../widgets/auth_prompt.dart';
```

- [ ] **Step 3: Commit**

```bash
git add smartstay-flutter/lib/pages/work_order/work_order_page.dart
git commit -m "feat(c-end): work order unauth overlay"
```

---

## Task 6: "我的"页面

**Files:**
- Create: `smartstay-flutter/lib/pages/my/my_page.dart`

- [ ] **Step 1: 创建 MyPage 组件**

```dart
// lib/pages/my/my_page.dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../blocs/auth/auth_bloc.dart';
import '../../blocs/auth/auth_event.dart';
import '../../blocs/auth/auth_state.dart';
import '../../core/api_client.dart';
import '../../widgets/login_bottom_sheet.dart';
import 'bill_detail_page.dart';

class MyPage extends StatefulWidget {
  const MyPage({super.key});

  @override
  State<MyPage> createState() => _MyPageState();
}

class _MyPageState extends State<MyPage> {
  Map<String, dynamic>? _currentOrder;
  Map<String, dynamic>? _billData;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final auth = context.read<AuthBloc>().state;
    if (auth.status != AuthStatus.authenticated) return;
    setState(() => _loading = true);
    try {
      final orderResp = await ApiClient().get('/api/orders/current');
      _currentOrder = orderResp.data as Map<String, dynamic>?;
      if (_currentOrder != null) {
        final billResp = await ApiClient().get('/api/orders/${_currentOrder!['id']}/bill');
        _billData = billResp.data as Map<String, dynamic>?;
      }
    } catch (_) {
      // 没有 active 订单时忽略
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocListener<AuthBloc, AuthState>(
      listener: (context, state) {
        if (state.status == AuthStatus.authenticated) _loadData();
      },
      child: Scaffold(
        appBar: AppBar(title: const Text('👤 我的'), backgroundColor: const Color(0xFF1A1A2E), foregroundColor: Colors.white),
        body: BlocBuilder<AuthBloc, AuthState>(
          builder: (context, auth) {
            if (auth.status == AuthStatus.authenticated) {
              return _buildAuthenticatedView(auth);
            }
            return _buildUnauthView();
          },
        ),
      ),
    );
  }

  Widget _buildUnauthView() {
    return ListView(children: [
      // 渐变登录卡片
      Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF1A1A2E), Color(0xFF16213E), Color(0xFF1677FF)],
            begin: Alignment.topLeft, end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(children: [
          Container(width: 56, height: 56,
            decoration: BoxDecoration(color: Colors.white.withOpacity(0.12), shape: BoxShape.circle),
            child: const Center(child: Text('🏨', style: TextStyle(fontSize: 26)))),
          const SizedBox(height: 12),
          const Text('智宿云酒店', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          Text('登录后享受完整入住服务', style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 10)),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: () => LoginBottomSheet.show(context),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 10),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(24),
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 16)]),
              child: const Text('立即登录', style: TextStyle(color: Color(0xFF1677FF), fontSize: 11, fontWeight: FontWeight.w700)),
            ),
          ),
        ]),
      ),
      // 设置菜单
      _buildSettingsCard(showLogout: false),
    ]);
  }

  Widget _buildAuthenticatedView(AuthState auth) {
    final grandTotal = _billData != null ? ((_billData!['grand_total'] as num?)?.toInt() ?? 0) : 0;
    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(children: [
        // 用户信息卡
        Container(
          margin: const EdgeInsets.all(12),
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF1A1A2E), Color(0xFF16213E), Color(0xFF1677FF)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(children: [
            Row(children: [
              Container(width: 48, height: 48,
                decoration: const BoxDecoration(
                  gradient: LinearGradient(colors: [Color(0xFF4096FF), Color(0xFF95DE64)]),
                  shape: BoxShape.circle,
                ),
                child: Center(child: Text(
                  (auth.name ?? '?').substring(0, 1),
                  style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800),
                ))),
              const SizedBox(width: 12),
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(auth.name ?? '', style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w800)),
                const SizedBox(height: 3),
                Text('身份证 ${_maskIdCard(auth.idCard ?? '')}', style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 9)),
                Text('手机 ${_maskPhone(auth.phone ?? '')}', style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 9)),
              ]),
            ]),
            if (_currentOrder != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
                child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  Text('🏨 当前入住', style: TextStyle(color: Colors.white.withOpacity(0.8), fontSize: 10)),
                  Text('${_currentOrder!['room_number'] ?? ''}房 · ${_currentOrder!['room_type'] ?? ''}',
                    style: const TextStyle(color: Color(0xFF7FFFA7), fontSize: 11, fontWeight: FontWeight.w700)),
                ]),
              ),
            ],
          ]),
        ),
        // 我的订单
        _buildSectionCard('📋 我的订单', [
          if (_currentOrder != null)
            _buildMenuItem('当前', '${_currentOrder!['room_number'] ?? ''}房', tag: '当前', tagColor: const Color(0xFF1677FF)),
          _buildMenuItem('历史', '暂无记录', tag: '历史', tagColor: const Color(0xFF999999)),
        ]),
        // 账单消费
        _buildSectionCard('💰 账单消费', [
          _buildMenuItem('当前账单', grandTotal > 0 ? '¥${(grandTotal / 100).toStringAsFixed(0)}' : '暂无账单',
            valueColor: const Color(0xFFFF4D4F), onTap: () {
              if (_billData != null && _currentOrder != null) {
                Navigator.push(context, MaterialPageRoute(
                  builder: (_) => BillDetailPage(orderId: _currentOrder!['id'])));
              }
            }),
        ]),
        // 设置
        _buildSettingsCard(showLogout: true),
        const SizedBox(height: 24),
      ]),
    );
  }

  Widget _buildSectionCard(String title, List<Widget> children) {
    return Container(margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10)]),
      child: Column(children: [
        Container(width: double.infinity, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: const BoxDecoration(color: Color(0xFFFAFBFC), borderRadius: BorderRadius.vertical(top: Radius.circular(14))),
          child: Text(title, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF1A1A2E)))),
        ...children,
      ]),
    );
  }

  Widget _buildMenuItem(String label, String value, {String? tag, Color? tagColor, Color? valueColor, VoidCallback? onTap}) {
    return InkWell(onTap: onTap,
      child: Padding(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        child: Row(children: [
          if (tag != null) ...[
            Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(color: tagColor?.withOpacity(0.1) ?? const Color(0xFFF5F5F5), borderRadius: BorderRadius.circular(4)),
              child: Text(tag, style: TextStyle(fontSize: 8, color: tagColor ?? const Color(0xFF999999), fontWeight: FontWeight.w600))),
            const SizedBox(width: 8),
          ],
          Expanded(child: Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF333333)))),
          Text(value, style: TextStyle(fontSize: valueColor != null ? 15 : 10, color: valueColor ?? const Color(0xFF333333), fontWeight: valueColor != null ? FontWeight.w800 : FontWeight.normal)),
          const SizedBox(width: 8),
          const Text('›', style: TextStyle(fontSize: 14, color: Color(0xFFDDDDDD))),
        ])),
    );
  }

  Widget _buildSettingsCard({required bool showLogout}) {
    return Container(margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10)]),
      child: Column(children: [
        if (showLogout) _buildMenuItem('🔑 修改密码', '', onTap: () {
          // TODO: 弹出修改密码弹窗
        }),
        _buildMenuItem('🏨 关于酒店', '', onTap: () {}),
        _buildMenuItem('📞 客服电话', '', onTap: () {}),
        if (showLogout)
          _buildMenuItem('🚪 退出登录', '', valueColor: const Color(0xFFFF4D4F), onTap: () {
            showDialog(context: context, builder: (ctx) => AlertDialog(
              title: const Text('确认退出'),
              content: const Text('确定要退出登录吗？'),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
                FilledButton(onPressed: () {
                  context.read<AuthBloc>().add(AuthLogoutRequested());
                  Navigator.pop(ctx);
                }, child: const Text('退出')),
              ],
            ));
          }),
      ]),
    );
  }

  String _maskIdCard(String idCard) {
    if (idCard.length <= 6) return idCard;
    return '${idCard.substring(0, 4)}****${idCard.substring(idCard.length - 4)}';
  }

  String _maskPhone(String phone) {
    if (phone.length <= 4) return phone;
    return '${phone.substring(0, 3)}****${phone.substring(phone.length - 4)}';
  }
}
```

- [ ] **Step 2: 验证编译**

Run: `cd smartstay-flutter && flutter analyze lib/pages/my/my_page.dart`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add smartstay-flutter/lib/pages/my/my_page.dart
git commit -m "feat(c-end): add MyPage with user info, orders, billing, settings"
```

---

## Task 7: 账单详情二级页

**Files:**
- Create: `smartstay-flutter/lib/pages/my/bill_detail_page.dart`

- [ ] **Step 1: 迁移 BillPage 逻辑到 BillDetailPage**

从 `lib/pages/bill/bill_page.dart` 迁移逻辑，改为接收 `orderId` 参数的二级页：

```dart
// lib/pages/my/bill_detail_page.dart
import 'package:flutter/material.dart';
import '../../core/api_client.dart';

class BillDetailPage extends StatefulWidget {
  final String orderId;
  const BillDetailPage({super.key, required this.orderId});

  @override
  State<BillDetailPage> createState() => _BillDetailPageState();
}

class _BillDetailPageState extends State<BillDetailPage> {
  // ... 从 bill_page.dart 迁移所有状态和逻辑
  // 修改 _fetchBill 直接使用 widget.orderId 而不是先查 /api/orders/current
  // 其余代码保持不变
}
```

- [ ] **Step 2: Commit**

```bash
git add smartstay-flutter/lib/pages/my/bill_detail_page.dart
git commit -m "feat(c-end): add BillDetailPage as secondary page"
```

---

## Task 8: 更新底部导航栏和路由

**Files:**
- Modify: `smartstay-flutter/lib/widgets/bottom_nav.dart`
- Modify: `smartstay-flutter/lib/app.dart`

- [ ] **Step 1: 修改 BottomNav，"账单"→"我的"**

```dart
// lib/widgets/bottom_nav.dart
final items = const [
  ('🏠', '首页'),
  ('💡', '控房'),
  ('🤖', '管家'),
  ('🔧', '服务'),
  ('👤', '我的'),  // 原 ('💰', '账单')
];
```

- [ ] **Step 2: 修改 AppRouter 路由**

在 `app.dart` 中：
1. 将 `/bill` 路由替换为 `/my` 路由（指向 MyPage）
2. 移除强制登录拦截逻辑，改为全白名单模式
3. 更新 Tab 索引映射

```dart
// app.dart 中的关键变更
import 'pages/my/my_page.dart';
// 移除 import 'pages/bill/bill_page.dart';

// 路由表
ShellRoute(
  builder: (context, state, child) {
    final index = _getTabIndex(state.uri.toString());
    return Scaffold(
      body: child,
      bottomNavigationBar: BottomNav(
        currentIndex: index,
        onTap: (i) {
          final paths = ['/home', '/room-control', '/ai-chat', '/work-orders', '/my'];
          GoRouter.of(context).go(paths[i]);
        },
      ),
    );
  },
  routes: [
    GoRoute(path: '/home', builder: (_, __) => const HomePage()),
    GoRoute(path: '/room-control', builder: (_, __) => const RoomControlPage()),
    GoRoute(path: '/ai-chat', builder: (_, __) => const AIChatPage()),
    GoRoute(path: '/work-orders', builder: (_, __) => const WorkOrderPage()),
    GoRoute(path: '/my', builder: (_, __) => const MyPage()),
    GoRoute(path: '/map', builder: (_, __) => const MapPage()),
    GoRoute(path: '/facility', builder: (_, __) => const FacilityPage()),
  ],
)

// Tab 索引映射
static int _getTabIndex(String path) {
  if (path.startsWith('/home') || path.startsWith('/map') || path.startsWith('/facility')) return 0;
  if (path.startsWith('/room-control')) return 1;
  if (path.startsWith('/ai-chat')) return 2;
  if (path.startsWith('/work-orders')) return 3;
  if (path.startsWith('/my')) return 4;
  return 0;
}
```

- [ ] **Step 3: 简化 redirect 逻辑**

移除强制登录拦截，改为：
```dart
redirect: (context, state) {
  final auth = authBloc.state;
  final loc = state.uri.toString();

  // 仅强制改密时拦截
  if (auth.status == AuthStatus.passwordChangeRequired) {
    if (loc != '/change-password') return '/change-password';
    return null;
  }

  // 所有路由都允许匿名访问（移除白名单机制）
  return null;
},
```

- [ ] **Step 4: 验证编译**

Run: `cd smartstay-flutter && flutter analyze`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add smartstay-flutter/lib/widgets/bottom_nav.dart smartstay-flutter/lib/app.dart
git commit -m "feat(c-end): update nav to 5 tabs, remove forced login redirect"
```

---

## Task 9: 集成测试和清理

- [ ] **Step 1: 完整编译检查**

Run: `cd smartstay-flutter && flutter analyze`
Expected: No errors

- [ ] **Step 2: 手动测试流程**

1. 冷启动 App → 应直接进入首页
2. 点击控房 Tab → 应显示置灰控件 + 底部登录引导
3. 点击"立即登录" → 应弹出底部登录弹窗
4. 点击管家 Tab → 应显示遮罩引导
5. 点击服务 Tab → 应显示遮罩引导
6. 点击我的 Tab → 应显示渐变登录卡片
7. 登录成功 → 弹窗关闭，页面刷新为已登录内容
8. 我的页 → 应显示个人信息、订单、账单、设置

- [ ] **Step 3: 清理旧文件**

删除不再作为 Tab 页面使用的 `bill_page.dart`（或保留但不引用）：
```bash
# 可选：保留原文件作为参考，或删除
git rm smartstay-flutter/lib/pages/bill/bill_page.dart
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(c-end): complete navigation redesign - 5 tabs, bottom sheet login, MyPage"
```
