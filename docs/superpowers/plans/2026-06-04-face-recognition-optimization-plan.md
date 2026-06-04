# 人脸识别功能优化实施计划
> **For agentic workers:** 使用 superpowers:executing-plans 逐 task 实施。Steps 使用 checkbox (`- [ ]`) 跟踪进度。

**Goal:** 修复人脸识别 bug + 提升体验和视觉质量，达到答辩交付标准
**Architecture:** 后端清理 debug 代码，B 端/C 端 UI 优化，Flutter AuthBloc 修复 bug
**Tech Stack:** Python/FastAPI, React/Ant Design, Flutter/Camera

---

## 文件结构

### 修改文件
| 文件 | Task | 改动说明 |
|------|------|---------|
| `backend/app/api/face.py` | 1 | 清理 debug print，替换为 logger |
| `smartstay-flutter/lib/blocs/auth/auth_bloc.dart` | 2 | 修复刷脸登录绕过 is_first_login 的 bug |
| `smartstay-flutter/lib/pages/login/face_login_page.dart` | 2+3+4+5+6+8 | 深色主题 + 引导框 + 分辨率 + 次数限制 + 错误状态 |
| `frontend/src/pages/front-desk/FaceCapture.tsx` | 7 | B 端摄像头引导框 |
| `frontend/src/pages/front-desk/CheckInModal.tsx` | 9 | 变量名清理 + 步骤描述优化 |

### 不改动文件
- `backend/app/aliyun/face.py` — API 封装正确，无需修改
- `backend/app/core/config.py` — 配置项不变
- `backend/app/models/guest.py` — 字段不变

---

## Task 1: 清理后端 debug print 语句
**文件:** `backend/app/api/face.py`

**改动:**
1. 在文件顶部添加 `import logging` 和 `logger = logging.getLogger(__name__)`
2. 将 `/api/face/search` 中 7 处 `print(f"[FACE SEARCH] ...")` 替换为 `logger.info(...)` 或 `logger.debug(...)`
3. 保留关键日志信息（活体检测结果、匹配结果、is_active 跳过），降级为 debug 级别

**具体替换:**
- `print(f"[FACE SEARCH] received {len(image_bytes)} bytes")` → `logger.debug("received %d bytes", len(image_bytes))`
- `print(f"[FACE SEARCH] living result: {living_result}")` → `logger.debug("living result: %s", living_result)`
- `print(f"[FACE SEARCH] liveness: suggestion=...")` → `logger.info("liveness: suggestion=%s, rate=%s, pass=%s", ...)`
- `print(f"[FACE SEARCH] liveness: no elements/results, ...")` → `logger.warning("liveness: no elements/results")`
- `print(f"[FACE SEARCH] search result: {search_result}")` → `logger.debug("search result: %s", search_result)`
- `print(f"[FACE SEARCH] match_list count={len(match_list)}")` → `logger.debug("match_list count=%d", len(match_list))`
- `print(f"[FACE SEARCH] guest {guest_uuid} is_active=False, skipping")` → `logger.info("guest %s is_active=False, skipping", guest_uuid)`

**验证:** `poetry run python -m py_compile app/api/face.py` 通过

---

## Task 2: 修复刷脸登录绕过 is_first_login 的 Bug
**文件:** `smartstay-flutter/lib/blocs/auth/auth_bloc.dart` + `smartstay-flutter/lib/pages/login/face_login_page.dart`

**现状：** `_onFaceLogin` 已经调用了 `GET /api/auth/me` 并在 state 中填充了 `isFirstLogin` 字段，但 `status` 始终写死为 `AuthStatus.authenticated`。

**改动：** 仅修改 `emit(AuthState(...))` 中的 `status` 字段，改为条件表达式。

**修改前（auth_bloc.dart）:**
```dart
emit(AuthState(
  status: AuthStatus.authenticated,  // Bug: 未用 isFirstLogin 决定 status
  userId: user['id'],
  ...
));
```

**修改后（auth_bloc.dart）:**
```dart
emit(AuthState(
  status: user['is_first_login'] == true
      ? AuthStatus.passwordChangeRequired
      : AuthStatus.authenticated,
  userId: user['id'],
  name: user['name'],
  idCard: user['id_card'],
  phone: user['phone'] ?? '',
  role: user['role'] ?? 'guest',
  isFirstLogin: user['is_first_login'] == true,
));
```

**修改（face_login_page.dart listener）:**
补充 `passwordChangeRequired` 处理，否则用户卡在刷脸页面无反应：
```dart
} else if (state.status == AuthStatus.passwordChangeRequired) {
  context.go('/change-password');
}
```

**验证:** flutter analyze 通过。手动测试：用 is_first_login=True 的住客刷脸 → 跳转修改密码页；用 is_first_login=False 的住客刷脸 → 进入首页。

---

## Task 3: C端刷脸页面适配深色主题
**文件:** `smartstay-flutter/lib/pages/login/face_login_page.dart`

**改动:**
1. Scaffold 背景色改为 `Color(0xFF0a0a1e)`
2. AppBar 改为透明背景 + 白色前景：
   ```dart
   AppBar(
     backgroundColor: Colors.transparent,
     elevation: 0,
     leading: IconButton(
       icon: const Icon(Icons.chevron_left, color: Colors.white, size: 28),
       onPressed: () => context.go('/login'),
     ),
     title: const Text('刷脸登录', style: TextStyle(color: Colors.white)),
   )
   ```
3. body 包裹在带渐变的 Container 中（与其他页面一致）
4. "开始刷脸" 按钮：背景色 `Color(0xFF2563eb)`，文字白色
5. "返回密码登录" 按钮：文字色 `Color(0xFF9ca3af)`
6. 提示文字颜色适配深色主题

**验证:** flutter analyze 通过

---

## Task 4: C端面部引导框
**文件:** `smartstay-flutter/lib/pages/login/face_login_page.dart`

**改动:**
1. 在 `Expanded(child: CameraPreview(...))` 外层包裹 `Stack`
2. 新增 `_buildFaceGuide()` 方法，返回一个半透明遮罩 + 圆形镂空：
   ```dart
   Widget _buildFaceGuide() {
     return CustomPaint(
       size: Size.infinite,
       painter: _FaceGuidePainter(),
     );
   }
   ```
3. 新增 `_FaceGuidePainter` 类（继承 CustomPainter）：
   - 绘制全屏半透明黑色遮罩（`Colors.black.withOpacity(0.5)`）
   - 中间镂空圆形（使用 `Path.combine` 减去圆形区域）
   - 圆形直径 = 屏幕宽度 × 0.55
   - 圆形位于屏幕上半部分（垂直居中偏上）
4. 圆形下方显示提示文字："请将面部对准圆框"
5. Stack 结构：`[CameraPreview, _buildFaceGuide(), 提示文字]`

**实现细节:**
```dart
class _FaceGuidePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.black.withOpacity(0.5);
    final path = Path()
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height));
    final circlePath = Path()
      ..addOval(Rect.fromCircle(
        center: Offset(size.width / 2, size.height * 0.38),
        radius: size.width * 0.275,
      ));
    final finalPath = Path.combine(PathOperation.difference, path, circlePath);
    canvas.drawPath(finalPath, paint);
    
    // Draw circle border
    final borderPaint = Paint()
      ..color = const Color(0xFF2563eb)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas.drawCircle(
      Offset(size.width / 2, size.height * 0.38),
      size.width * 0.275,
      borderPaint,
    );
  }
  
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
```

**验证:** flutter analyze 通过

---

## Task 5: 提升摄像头分辨率
**文件:** `smartstay-flutter/lib/pages/login/face_login_page.dart`

**改动:**
1. 将 `_controller = CameraController(frontCamera, ResolutionPreset.medium)` 改为 `ResolutionPreset.high`

**验证:** flutter analyze 通过

---

## Task 6: 刷脸登录尝试次数限制
**文件:** `smartstay-flutter/lib/pages/login/face_login_page.dart`

**改动:**
1. 在 State 中添加 `int _attemptCount = 0`
2. 在 `_capture()` 方法开头检查 `if (_attemptCount >= 3) return;`
3. 在 listener 中判断失败时 +1（所有失败均计数：网络超时、活体未通过、未匹配等，不做区分）
4. 在 builder 中，当 `_attemptCount >= 3` 时：
   - 拍照按钮变灰（disabled）
   - 下方显示红色提示文字："尝试次数已达上限，请使用密码登录"
5. 在页面初始化时重置 `_attemptCount = 0`

**具体实现:**
```dart
// 在 listener 中:
} else if (state.status == AuthStatus.unauthenticated && state.error != null) {
  if (mounted) {
    setState(() => _attemptCount++);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(state.error!), backgroundColor: Colors.red),
    );
  }
}

// 在 builder 中:
if (_attemptCount >= 3)
  const Padding(
    padding: EdgeInsets.only(top: 8),
    child: Text('尝试次数已达上限，请使用密码登录',
      style: TextStyle(color: Colors.redAccent, fontSize: 13)),
  ),
```

**验证:** flutter analyze 通过，连续失败3次按钮变灰

---

## Task 7: B端面部引导框
**文件:** `frontend/src/pages/front-desk/FaceCapture.tsx`

**改动:**
1. 在 video/canvas 的父容器上添加圆形引导遮罩
2. 使用纯 CSS 实现（不引入新依赖）：
   ```tsx
   <div style={{ position: 'relative', width: 300, height: 300, margin: '0 auto' }}>
     {/* Camera preview */}
     <video ... style={{ width: 300, borderRadius: 8, ... }} />
     
     {/* Face guide overlay */}
     <div style={{
       position: 'absolute', inset: 0,
       borderRadius: 8,
       background: 'radial-gradient(circle at center, transparent 35%, rgba(0,0,0,0.5) 35%)',
       pointerEvents: 'none',
     }} />
     
     {/* Guide circle border */}
     <div style={{
       position: 'absolute',
       top: '50%', left: '50%',
       transform: 'translate(-50%, -50%)',
       width: 150, height: 150,
       border: '3px solid #2563eb',
       borderRadius: '50%',
       pointerEvents: 'none',
     }} />
     
     {/* Guide text */}
     <div style={{
       position: 'absolute', bottom: 8, left: 0, right: 0,
       textAlign: 'center', color: '#9ca3af', fontSize: 12,
     }}>请将面部对准圆框</div>
   </div>
   ```
3. captured 状态下隐藏引导遮罩（显示已拍照片）

**验证:** tsc --noEmit 通过

---

## Task 8: C端摄像头错误状态
**文件:** `smartstay-flutter/lib/pages/login/face_login_page.dart`

**改动:**
1. 在 State 中添加 `String? _cameraError`
2. 修改 `_initCamera()`：
   - 失败时设置 `_cameraError = '摄像头初始化失败'` 并 `setState`
   - 去掉 SnackBar
3. 在 builder 中，当 `_cameraError != null` 时显示：
   - 错误图标（Icons.error_outline）
   - 错误文字
   - 重试按钮（调用 `_initCamera()`）

**具体实现:**
```dart
// builder 中:
if (_cameraError != null)
  return Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.error_outline, color: Colors.redAccent, size: 48),
        const SizedBox(height: 16),
        Text(_cameraError!, style: const TextStyle(color: _muted, fontSize: 14)),
        const SizedBox(height: 16),
        ElevatedButton(
          onPressed: () { setState(() { _cameraError = null; _initialized = false; }); _initCamera(); },
          style: ElevatedButton.styleFrom(backgroundColor: _blue),
          child: const Text('重试', style: TextStyle(color: Colors.white)),
        ),
      ],
    ),
  );
```

**验证:** flutter analyze 通过

---

## Task 9: B端变量名清理 + 步骤描述优化
**文件:** `frontend/src/pages/front-desk/CheckInModal.tsx`

**改动:**
1. 变量名 `ocrLoading` → `detectLoading`（实际调用的是 detect_face 接口检测人脸，不是 OCR）
2. 所有引用 `ocrLoading` 的地方同步改为 `detectLoading`（setOcrLoading → setDetectLoading）
3. 步骤1标题 `"1. 上传身份证照片"` → `"1. 上传身份证正面照片"`（与按钮文字保持一致）
4. 在步骤区域添加说明文字：`"用于人脸比对验证，确保住客身份与身份证一致"`

**验证:** tsc --noEmit 通过

---

## Task 10: 最终验证
**验证步骤:**
1. `cd backend && poetry run python -m py_compile app/api/face.py` — 后端编译通过
2. `cd frontend && npx tsc --noEmit` — 前端类型检查通过
3. `cd smartstay-flutter && flutter analyze` — Flutter 静态分析通过
4. 手动验证场景：
   - C端刷脸登录（is_first_login=True）→ 跳转修改密码页
   - C端刷脸登录（is_first_login=False）→ 进入首页
   - C端连续3次失败 → 按钮变灰
   - C端刷脸页面深色主题 + 圆形引导框
   - B端开房人脸录入引导框
   - 后端控制台无 print 语句

---

## 假设与默认值

1. 阿里云 API 调用逻辑不变，仅清理日志
2. 摄像头分辨率 medium → high，不影响性能
3. 尝试次数限制为客户端实现（3次），不依赖后端
4. 引导框为纯视觉引导，不涉及人脸检测算法
5. B 端引导框使用纯 CSS，不引入新依赖
6. 不新增 /api/face/ocr-idcard 接口（后续扩展）








