
# 人脸识别登录功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SmartStay 人脸识别登录功能

**Architecture:** B 端开房时录入人客人脸并匹配身份证，C 端通过刷脸+活体检测登录。后端通过阿里云 API 实现人脸检测/比对/活体检测/搜索，人脸数据存储在阿里云人脸库中，本地只存 face_id。

**Tech Stack:** FastAPI + SQLModel + Aliyun SDK + PostgreSQL/pgvector + React 19 + Ant Design + Flutter + BLoC + GoRouter + Aliyun Vision API

---

### 文件结构

**新建文件：**

| 文件 | 说明 |
|------|------|
| `backend/app/aliyun/__init__.py` | Aliyun 服务模块初始化 |
| `backend/app/aliyun/face.py` | Aliyun 人脸 API 封装 |
| `backend/app/api/face.py` | 人脸识别相关 API 路由 |
| `frontend/src/pages/front-desk/FaceCapture.tsx` | B 端摄像头拍照组件 |
| `smartstay-flutter/lib/pages/login/face_login_page.dart` | C 端刷脸登录页面 |

**修改文件：**

| 文件 | 修改内容 |
|------|---------|
| `backend/app/core/config.py` | 新增阿里云 AccessKey 配置 |
| `backend/app/models/guest.py` | 新增 face_id, face_registered 字段 |
| `backend/app/main.py` | 注册 face 路由 |
| `.env` | 添加阿里云配置项 |
| `frontend/src/pages/front-desk/CheckInModal.tsx` | 集成人脸录入步骤 |
| `smartstay-flutter/pubspec.yaml` | 添加 camera 依赖 |
| `smartstay-flutter/lib/blocs/auth/auth_event.dart` | 新增 AuthFaceLoginRequested |
| `smartstay-flutter/lib/blocs/auth/auth_state.dart` | 新增 faceLoginLoading |
| `smartstay-flutter/lib/blocs/auth/auth_bloc.dart` | 处理刷脸登录事件 |
| `smartstay-flutter/lib/app.dart` | 添加刷脸页面路由 |

---

## Task 1: 后端阿里云配置 + 人脸服务模块

**Files:**
- Create: `backend/app/aliyun/__init__.py`
- Create: `backend/app/aliyun/face.py`
- Modify: `backend/app/core/config.py`
- Modify: `.env`

### Step 1: 新增阿里云配置项

**修改 `backend/app/core/config.py`**，在 `Settings` 类中新增：

```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 阿里云配置
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_REGION_ID: str = "cn-shanghai"
    ALIYUN_FACE_DB_NAME: str = "smartstay_faces"
```

**修改 `.env`**，添加：

```
ALIYUN_ACCESS_KEY_ID=你的AccessKeyID
ALIYUN_ACCESS_KEY_SECRET=你的AccessKeySecret
```

### Step 2: 创建 Aliyun 服务模块

**创建 `backend/app/aliyun/__init__.py`** 为空文件。

**创建 `backend/app/aliyun/face.py`**，封装阿里云人脸 API：

```python
import base64
import json
from io import BytesIO
from typing import Optional

from alibabacloud_facebody20191230.client import Client as FacebodyClient
from alibabacloud_facebody20191230 import models as facebody_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from app.core.config import settings


def _create_client() -> FacebodyClient:
    """创建阿里云 Facebody 客户端"""
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
    )
    config.endpoint = f"facebody.{settings.ALIYUN_REGION_ID}.aliyuncs.com"
    return FacebodyClient(config)


def detect_face(image_bytes: bytes) -> dict:
    """DetectFace — 检测人脸质量"""
    client = _create_client()
    request = facebody_models.DetectFaceRequest(
        image_url_or_buf=BytesIO(image_bytes)
    )
    runtime = util_models.RuntimeOptions()
    response = client.detect_face_with_options(request, runtime)
    return response.body.to_map()


def compare_face(image_a_bytes: bytes, image_b_bytes: bytes) -> dict:
    """CompareFace — 人脸比对 1:1"""
    client = _create_client()
    request = facebody_models.CompareFaceRequest(
        image_url_or_buf_a=BytesIO(image_a_bytes),
        image_url_or_buf_b=BytesIO(image_b_bytes),
    )
    runtime = util_models.RuntimeOptions()
    response = client.compare_face_with_options(request, runtime)
    return response.body.to_map()


def detect_living_face(image_bytes: bytes) -> dict:
    """DetectLivingFace — 静默活体检测"""
    client = _create_client()
    request = facebody_models.DetectLivingFaceRequest(
        image_url_or_buf=BytesIO(image_bytes)
    )
    runtime = util_models.RuntimeOptions()
    response = client.detect_living_face_with_options(request, runtime)
    return response.body.to_map()


def add_face(db_name: str, entity_id: str, image_bytes: bytes) -> dict:
    """AddFace — 添加人脸到人脸库"""
    client = _create_client()
    request = facebody_models.AddFaceRequest(
        db_name=db_name,
        entity_id=entity_id,
        image_url_or_buf=BytesIO(image_bytes),
    )
    runtime = util_models.RuntimeOptions()
    response = client.add_face_with_options(request, runtime)
    return response.body.to_map()


def search_face(db_name: str, image_bytes: bytes) -> dict:
    """SearchFace — 人脸搜索 1:N"""
    client = _create_client()
    request = facebody_models.SearchFaceRequest(
        db_name=db_name,
        image_url_or_buf=BytesIO(image_bytes),
        max_num_return=5,
    )
    runtime = util_models.RuntimeOptions()
    response = client.search_face_with_options(request, runtime)
    return response.body.to_map()


def create_face_db(db_name: str) -> dict:
    """CreateFaceDb — 创建人脸库"""
    client = _create_client()
    request = facebody_models.CreateFaceDbRequest(name=db_name)
    runtime = util_models.RuntimeOptions()
    response = client.create_face_db_with_options(request, runtime)
    return response.body.to_map()
```

### Step 3: 验证

```bash
cd backend && poetry run python -m py_compile app/main.py
```

Expected: 编译通过，无错误。

### Step 4: Commit

```bash
git add backend/app/aliyun/ backend/app/core/config.py .env
git commit -m "feat: add aliyun face service module"

---

## Task 2: 后端人脸 API 路由 + 数据库变更

**Files:**
- Create: `backend/app/api/face.py`
- Modify: `backend/app/models/guest.py`
- Modify: `backend/app/main.py`

### Step 1: Guest 模型新增字段

**修改 `backend/app/models/guest.py`**，在 Guest 类新增：

```python
class Guest(SQLModel, table=True):
    __tablename__ = "guests"
    
    # ... 现有字段 ...
    
    face_id: Optional[str] = Field(default=None, max_length=64)
    face_registered: bool = Field(default=False)
```

### Step 2: 创建人脸 API 路由

**创建 `backend/app/api/face.py`**：

```python
import base64
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.security import create_access_token, create_refresh_token
from app.models.guest import Guest
from app.aliyun.face import (
    detect_face,
    compare_face,
    detect_living_face,
    add_face,
    search_face,
)
from app.core.config import settings

router = APIRouter(prefix="/api/face", tags=["face"])


@router.post("/detect")
async def detect_face_endpoint(file: UploadFile = File(...)):
    """DetectFace — 检查人脸质量"""
    image_bytes = await file.read()
    result = detect_face(image_bytes)
    # 简化返回关键信息
    data = result.get("data", {})
    face_count = len(data.get("faceCount", [])) if data else 0
    return {"face_count": face_count, "quality_ok": face_count > 0}


@router.post("/verify")
async def verify_face(
    id_card_image: UploadFile = File(...),
    live_image: UploadFile = File(...),
):
    """CompareFace — 身份证照片 vs 本人脸"""
    id_card_bytes = await id_card_image.read()
    live_bytes = await live_image.read()
    
    result = compare_face(id_card_bytes, live_bytes)
    data = result.get("data", {})
    confidence = (data.get("confidence", 0) if data else 0) / 100.0
    
    return {
        "matched": confidence >= 0.8,
        "confidence": confidence,
    }


@router.post("/register")
async def register_face(
    guest_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Guest = Depends(require_role("front_desk")),
):
    """AddFace — 添加人脸到阿里云人脸库"""
    image_bytes = await file.read()
    
    result = add_face(settings.ALIYUN_FACE_DB_NAME, guest_id, image_bytes)
    data = result.get("data", {})
    face_id = (data.get("faceId", [])[0] if data and data.get("faceId") else None)
    
    if not face_id:
        raise HTTPException(status_code=500, detail="人脸注册失败")
    
    # 更新数据库
    stmt = select(Guest).where(Guest.id == uuid.UUID(guest_id))
    result_db = await db.execute(stmt)
    guest = result_db.scalar_one_or_none()
    if guest:
        guest.face_id = face_id
        guest.face_registered = True
        db.add(guest)
        await db.commit()
    
    return {"success": True, "face_id": face_id}


@router.post("/search")
async def search_face_login(
    file: UploadFile = File(...),
):
    """SearchFace — 刷脸登录（活体检测 + 人脸搜索）"""
    image_bytes = await file.read()
    
    # 1. 活体检测
    living_result = detect_living_face(image_bytes)
    living_data = living_result.get("data", {})
    if not living_data or living_data.get("confidence", 0) < 0.5:
        raise HTTPException(status_code=400, detail="活体检测未通过")
    
    # 2. 人脸搜索
    search_result = search_face(settings.ALIYUN_FACE_DB_NAME, image_bytes)
    search_data = search_result.get("data", {})
    match_list = search_data.get("matchList", []) if search_data else []
    
    if not match_list:
        raise HTTPException(status_code=404, detail="未找到匹配的人脸，请先到前台登记入住")
    
    best_match = match_list[0]
    confidence = best_match.get("confidence", 0) / 100.0
    
    if confidence < 0.85:
        raise HTTPException(status_code=400, detail="人脸匹配度不足，请重试")
    
    entity_id = best_match.get("entityId")
    
    # 3. 签发 JWT
    token_data = {"sub": entity_id, "role": "guest", "user_type": "guest"}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "success": True,
        "guest_id": entity_id,
        "confidence": confidence,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
```

### Step 3: 注册路由

**修改 `backend/app/main.py`**：

```python
from app.api.face import router as face_router

# 在 include_router 区域添加
app.include_router(face_router)
```

### Step 4: 验证

```bash
cd backend && poetry run python -m py_compile app/main.py
```

Expected: 编译通过，无错误。

### Step 5: Commit

```bash
git add backend/app/api/face.py backend/app/models/guest.py backend/app/main.py
git commit -m "feat: add face recognition API routes"
```

---

## Task 3: B 端前端 — 人脸录入组件

**Files:**
- Create: `frontend/src/pages/front-desk/FaceCapture.tsx`
- Modify: `frontend/src/pages/front-desk/CheckInModal.tsx`

### Step 1: 创建摄像头拍照组件

**创建 `frontend/src/pages/front-desk/FaceCapture.tsx`**：

```tsx
import { useRef, useState, useEffect } from 'react';

interface FaceCaptureProps {
  onCapture: (blob: Blob) => void;
  onRetry: () => void;
  captured: Blob | null;
}

export default function FaceCapture({ onCapture, onRetry, captured }: FaceCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
      .then(s => {
        setStream(s);
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => setError('请允许使用摄像头'));
    return () => stream?.getTracks().forEach(t => t.stop());
  }, []);

  const capture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')!.drawImage(video, 0, 0);
    canvas.toBlob(blob => { if (blob) onCapture(blob); }, 'image/jpeg');
  };

  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div>
      {captured ? (
        <img src={URL.createObjectURL(captured)} alt="captured" style={{ width: 300 }} />
      ) : (
        <video ref={videoRef} autoPlay playsInline style={{ width: 300 }} />
      )}
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      <button onClick={captured ? onRetry : capture}>
        {captured ? '重新拍摄' : '拍照'}
      </button>
    </div>
  );
}
```

### Step 2: 集成到 CheckInModal

**打开 `frontend/src/pages/front-desk/CheckInModal.tsx`**，理解现有结构后在开房表单新增人脸录入步骤。在表单提交前加入：

1. OCR 身份证识别 → 显示证件照预览
2. 调用 FaceCapture 组件拍摄本人脸
3. 调用 `/api/face/verify` 比对
4. 比对通过后调用 `/api/face/register` 注册人脸
5. 比对通过后才允许开房

> 详细前端代码参考 CheckInModal 现有模式：使用 Ant Design Modal + Form，调用 apiClient.post()

### Step 3: 验证

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
```

### Step 4: Commit

```bash
git add frontend/src/pages/front-desk/FaceCapture.tsx frontend/src/pages/front-desk/CheckInModal.tsx
git commit -m "feat: integrate face capture in check-in modal"
```

---

## Task 4: C 端 Flutter — 刷脸登录

**Files:**
- Modify: `smartstay-flutter/pubspec.yaml`
- Create: `smartstay-flutter/lib/pages/login/face_login_page.dart`
- Modify: `smartstay-flutter/lib/blocs/auth/auth_event.dart`
- Modify: `smartstay-flutter/lib/blocs/auth/auth_state.dart`
- Modify: `smartstay-flutter/lib/blocs/auth/auth_bloc.dart`
- Modify: `smartstay-flutter/lib/app.dart`

### Step 1: 添加 camera 依赖

**修改 `smartstay-flutter/pubspec.yaml`**，在 dependencies 中添加：

```yaml
dependencies:
  # ... 现有依赖 ...
  camera: ^0.11.1
```

### Step 2: 新增 Auth 事件

**修改 `smartstay-flutter/lib/blocs/auth/auth_event.dart`**：

```dart
class AuthFaceLoginRequested {
  final List<int> imageBytes;
  AuthFaceLoginRequested(this.imageBytes);
}
```

### Step 3: 修改 AuthState

**修改 `smartstay-flutter/lib/blocs/auth/auth_state.dart`**，在 `AuthStatus` 枚举中新增：

```dart
enum AuthStatus { initial, loading, authenticated, unauthenticated, passwordChangeRequired, faceLoginLoading }
```

### Step 4: 处理刷脸登录逻辑

**修改 `smartstay-flutter/lib/blocs/auth/auth_bloc.dart`**，在 `on<AuthFaceLoginRequested>` 处理器中：

```dart
on<AuthFaceLoginRequested>((event, emit) async {
  emit(state.copyWith(status: AuthStatus.faceLoginLoading));
  try {
    // 1. 上传照片到后端 /api/face/search
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(event.imageBytes, filename: 'face.jpg'),
    });
    final response = await _api.post('/api/face/search', data: formData);
    
    // 2. 保存 token
    await _api.setTokens(response.data['access_token'], response.data['refresh_token']);
    
    // 3. 获取用户信息
    final userResp = await _api.get('/api/auth/me');
    final user = userResp.data;
    
    emit(AuthState(
      status: AuthStatus.authenticated,
      userId: user['id'],
      name: user['name'],
      idCard: user['id_card'],
      phone: user['phone'] ?? '',
      role: user['role'] ?? 'guest',
      isFirstLogin: user['is_first_login'] ?? false,
    ));
  } catch (e) {
    emit(state.copyWith(status: AuthStatus.unauthenticated, error: '刷脸登录失败'));
  }
});
```

### Step 5: 创建刷脸页面

**创建 `smartstay-flutter/lib/pages/login/face_login_page.dart`**：

```dart
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../blocs/auth/auth_bloc.dart';

class FaceLoginPage extends StatefulWidget {
  const FaceLoginPage({super.key});
  @override
  State<FaceLoginPage> createState() => _FaceLoginPageState();
}

class _FaceLoginPageState extends State<FaceLoginPage> {
  CameraController? _controller;
  List<CameraDescription>? _cameras;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    _cameras = await availableCameras();
    if (_cameras == null || _cameras!.isEmpty) return;
    final frontCamera = _cameras!.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
      orElse: () => _cameras!.first,
    );
    _controller = CameraController(frontCamera, ResolutionPreset.medium);
    await _controller!.initialize();
    if (mounted) setState(() {});
  }

  Future<void> _capture() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    final xFile = await _controller!.takePicture();
    final bytes = await xFile.readAsBytes();
    if (mounted) {
      context.read<AuthBloc>().add(AuthFaceLoginRequested(bytes));
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('刷脸登录')),
      body: BlocConsumer<AuthBloc, AuthState>(
        listener: (context, state) {
          if (state.status == AuthStatus.authenticated) {
            context.go('/home');
          } else if (state.status == AuthStatus.unauthenticated && state.error != null) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(state.error!)),
            );
          }
        },
        builder: (context, state) {
          if (_controller == null || !_controller!.value.isInitialized) {
            return const Center(child: CircularProgressIndicator());
          }
          return Column(
            children: [
              Expanded(child: CameraPreview(_controller!)),
              const SizedBox(height: 16),
              if (state.status == AuthStatus.faceLoginLoading)
                const CircularProgressIndicator()
              else
                ElevatedButton(
                  onPressed: _capture,
                  child: const Text('开始刷脸'),
                ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () => context.go('/login'),
                child: const Text('返回密码登录'),
              ),
            ],
          );
        },
      ),
    );
  }
}
```

### Step 6: 注册路由

**修改 `smartstay-flutter/lib/app.dart`**，添加：

```dart
// 在 GoRouter routes 中添加
GoRoute(path: '/face-login', builder: (context, state) => const FaceLoginPage()),
```

### Step 7: 验证

```bash
cd smartstay-flutter && flutter analyze
```

Expected: 0 errors, 0 warnings。

### Step 8: Commit

```bash
git add smartstay-flutter/pubspec.yaml smartstay-flutter/lib/pages/login/face_login_page.dart smartstay-flutter/lib/blocs/auth/ smartstay-flutter/lib/app.dart
git commit -m "feat: add face login for C-end Flutter"
```

---

## Task 5: 集成验证

**Files:** 无需修改

### Step 1: 全部验证

```bash
# 后端
cd backend && poetry run python -m py_compile app/main.py
cd backend && poetry run pytest -x -q

# 前端
cd frontend && npx tsc --noEmit
cd frontend && npm run lint

# Flutter
cd smartstay-flutter && flutter analyze
```

Expected: 全部通过。

### Step 2: 更新 feature_list.json

在 feature_list.json 中新增条目：

```json
{
  "id": "F011",
  "name": "人脸识别登录",
  "status": "done",
  "created": "2026-06-01",
  "evidence": [
    "阿里云人脸 API 服务模块 (backend/app/aliyun/face.py)",
    "人脸 API 路由 (backend/app/api/face.py)",
    "B 端摄像头拍照组件 (frontend/src/pages/front-desk/FaceCapture.tsx)",
    "C 端刷脸登录页面 (smartstay-flutter/lib/pages/login/face_login_page.dart)",
    "后端 py_compile + pytest 通过",
    "前端 tsc --noEmit 通过",
    "Flutter analyze 通过"
  ]
}
```

### Step 3: 更新 session-handoff.md

记录当前状态，说明人脸识别功能已实现。

### Step 4: Commit

```bash
git add feature_list.json session-handoff.md
git commit -m "feat: complete face recognition login feature"
```

```
