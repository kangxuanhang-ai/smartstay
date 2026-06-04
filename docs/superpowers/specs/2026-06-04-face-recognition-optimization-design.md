# 人脸识别功能优化设计说明书

**日期**：2026-06-04
**范围**：后端 `/api/face` 路由、阿里云 API 封装、B 端 `CheckInModal` + `FaceCapture`、C 端 `FaceLoginPage` + `AuthBloc`
**依赖**：F013（人脸识别登录原始实现）

---

## 现状分析

### 当前人脸识别架构
```
B 端开房: 上传身份证照片 → detect_face(检测人脸) → 拍住客照片 → compare_face(1:1比对) → register(加入人脸库)
C 端登录: 前置摄像头拍照 → detect_living_face(活体检测) → search_face(1:N搜索) → 签发JWT
```

### 已发现问题
| # | 问题 | 严重程度 | 影响 |
|---|------|----------|------|
| 1 | C端刷脸登录绕过 is_first_login 检查 | 严重 | 首次入住住客刷脸后不会被强制改密 |
| 2 | 后端 /api/face/search 有7处 debug print | 高 | 答辩时控制台刷调试信息 |
| 3 | C端刷脸页面用白色默认主题，跟全app深色风格不搭 | 高 | 视觉突兀，答辩扣分 |
| 4 | C端摄像头没有面部引导框/圆形遮罩 | 高 | 用户不知道把脸放哪里，体验差 |
| 5 | B端 FaceCapture 没有引导框 | 高 | 同上 |
| 6 | C端摄像头用 ResolutionPreset.medium | 中 | 人脸识别精度受影响 |
| 7 | 无刷脸登录尝试次数限制 | 中 | 设计文档要求3次上限，实际无限 |
| 8 | B端代码变量名 ocrLoading 有误导性（实际是人脸检测非OCR） | 中 | 代码可读性差，答辩时被追问 |
| 9 | C端摄像头初始化失败只有SnackBar，无页面错误状态 | 低 | 初始化失败后页面空白 |
| 10 | 设计文档中的 /api/face/ocr-idcard 未实现 | 低 | 功能缺口 |

---

## 优化方案

### 1. 修复刷脸登录强制改密 Bug

**问题根因：** `auth_bloc.dart` 的 `_onFaceLogin` 方法已经调用了 `/api/auth/me` 并在 state 中填充了 `isFirstLogin` 字段，但 `status` 始终写死为 `AuthStatus.authenticated`，没有根据 `is_first_login` 做条件判断。

**修复：** 仅需在 `emit(AuthState(...))` 中将 `status` 改为条件表达式——对齐密码登录 `_onLogin` 的逻辑。

**改动文件：** `smartstay-flutter/lib/blocs/auth/auth_bloc.dart` + `smartstay-flutter/lib/pages/login/face_login_page.dart`

**逻辑变更（auth_bloc.dart）：**
```
_faceLogin 成功后（已有 setTokens + GET /api/auth/me）:
  status: user['is_first_login'] == true
      ? AuthStatus.passwordChangeRequired
      : AuthStatus.authenticated
```

**逻辑变更（face_login_page.dart）：**
在 listener 中补充 `passwordChangeRequired` 处理，否则 BLoC 发出该状态后用户会卡在刷脸页面无反应：
```dart
} else if (state.status == AuthStatus.passwordChangeRequired) {
  context.go('/change-password');
}
```

**验证：** 
- 用 is_first_login=True 的住客刷脸登录 → 应跳转到修改密码页
- 用 is_first_login=False 的住客刷脸登录 → 直接进入首页

---

### 2. 清理后端 debug print 语句

**改动文件：** `backend/app/api/face.py`

将 `/api/face/search` 中的 7 处 `print()` 替换为 `logging.getLogger(__name__).info/debug`，或直接删除。建议保留关键信息（活体检测结果、匹配结果）作为 info 级别日志。

---

### 3. C端刷脸页面适配深色主题

**改动文件：** `smartstay-flutter/lib/pages/login/face_login_page.dart`

变更：
- Scaffold 背景色改为 `Color(0xFF0a0a1e)`
- AppBar 改为透明背景 + 白色前景（与其他页面一致）
- 添加深色渐变背景 Container
- 按钮、文字颜色适配深色主题
- 错误提示改用深色主题 SnackBar

---

### 4. C端面部引导框

**改动文件：** `smartstay-flutter/lib/pages/login/face_login_page.dart`

在 CameraPreview 上叠加一个圆形面部引导遮罩：
- 使用 CustomPainter 绘制半透明黑色遮罩
- 中间镂空一个圆形区域（面部引导框）
- 圆形区域上方/下方显示提示文字："请将面部对准圆框"
- 引导框大小约占屏幕宽度 60%

**实现方式：** 使用 Stack + ClipPath 或 CustomPainter，不引入新依赖。

---

### 5. B端面部引导框

**改动文件：** `frontend/src/pages/front-desk/FaceCapture.tsx`

在 video/canvas 上叠加圆形引导遮罩：
- 使用 CSS 实现：外层 div 半透明黑色背景
- 内层 div 圆形镂空（CSS clip-path 或 mask）
- 提示文字："请将面部对准圆框"

---

### 6. 提升摄像头分辨率

**改动文件：** `smartstay-flutter/lib/pages/login/face_login_page.dart`

变更：`ResolutionPreset.medium` → `ResolutionPreset.high`

---

### 7. 刷脸登录尝试次数限制

**改动文件：** `smartstay-flutter/lib/pages/login/face_login_page.dart`

实现方式：
- FaceLoginPage 中维护 `_attemptCount` 计数器（最多3次）
- 每次失败 +1，达到3次后禁用拍照按钮，显示"尝试次数已达上限，请使用密码登录"
- 登录成功或切换页面时重置

**验证：** 连续失败3次 → 按钮变灰 + 提示文字

---

### 8. B端代码变量名清理

**改动文件：** `frontend/src/pages/front-desk/CheckInModal.tsx`

变更：
- 变量名 `ocrLoading` → `detectLoading`（实际调用的是 detect_face 接口检测人脸，不是 OCR）
- 步骤1标题 "上传身份证照片" → "上传身份证正面照片"（与按钮文字保持一致）
- 添加步骤说明文字："用于人脸比对验证，确保住客身份与身份证一致"

---

### 9. C端摄像头错误状态

**改动文件：** `smartstay-flutter/lib/pages/login/face_login_page.dart`

变更：
- `_initCamera` 失败时设置 `_error` 状态
- build 中检查 `_error`，显示错误图标 + 文字 + 重试按钮
- 去掉 SnackBar（不可靠，页面可能已 unmount）

---

## 不改动项

- `/api/face/ocr-idcard` 接口：原设计文档中定义但从未实现，本次不新增。B 端当前方案（手动输入 + 人脸比对）功能完整，OCR 可作为后续扩展。
- 阿里云 API 封装层 (`aliyun/face.py`)：无需修改，API 调用逻辑正确。
- `/api/face/search` 接口逻辑：活体检测 + 人脸搜索 + JWT 签发流程正确，只需清理 print 语句。

---

## 验证方式

| 场景 | 预期结果 |
|------|----------|
| C端刷脸登录（is_first_login=True） | 活体通过 → 搜索成功 → BLoC发出passwordChangeRequired → 跳转修改密码页 |
| C端刷脸登录（is_first_login=False） | 活体通过 → 搜索成功 → BLoC发出authenticated → 进入首页 |
| C端连续3次刷脸失败 | 按钮变灰，提示"已达上限" |
| C端刷脸页面视觉 | 深色主题，圆形引导框，提示文字 |
| B端开房人脸录入 | 身份证上传 + 摄像头引导框 + 比对 + 注册 |
| 后端控制台 | 无 print 语句，使用 logger |
| py_compile | 通过 |
| tsc --noEmit | 通过 |
| flutter analyze | 通过 |


