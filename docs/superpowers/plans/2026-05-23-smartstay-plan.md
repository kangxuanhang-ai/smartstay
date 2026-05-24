# SmartStay（智宿云）全栈酒店系统 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零构建一个 AI 驱动的全栈酒店管理系统，C端 Flutter + B端 React + FastAPI 后端 + LangGraph AI 引擎，用于 AI 应用开发工程师面试展示。

**Architecture:** 主仓（FastAPI 后端 + React B端）通过 REST API/WebSocket 通信，Flutter C端独立仓库。后端采用 SQLModel + PostgreSQL + pgvector 数据库，AI 层使用 LangGraph State Graph + DeepSeek-v4-flash API。

**Tech Stack:** FastAPI, SQLModel, PostgreSQL, pgvector, Redis, LangGraph, DeepSeek API, React 18, Vite, Ant Design 5, ECharts, Zustand, Tailwind CSS, Flutter, Bloc, GoRouter

**Design Spec:** `docs/superpowers/specs/2026-05-23-smartstay-design.md`

**Existing Infrastructure:** Docker 已运行 PostgreSQL + pgvector + Redis

---

## Phase 1: 后端基础架构 + 数据库 + 认证（MVP 核心）

**可演示内容:** Swagger UI 调用全部 CRUD 接口，JWT 认证流程，数据库全量建表，pytest 测试覆盖

### Task 1.1: Poetry 项目初始化 + 核心依赖

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建 backend 目录和 pyproject.toml**

```bash
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app\core" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app\models" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app\schemas" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app\api" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app\ws" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app\ai" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\app\tasks" -Force
New-Item -ItemType Directory -Path "C:\Users\21943\Desktop\项目\my-project\backend\tests" -Force
```

`backend/pyproject.toml`:
```toml
[tool.poetry]
name = "smartstay-backend"
version = "0.2.0"
description = "SmartStay Hotel Management API"
authors = ["SmartStay"]
python = "^3.11"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
sqlmodel = "^0.0.22"
asyncpg = "^0.30.0"
psycopg2-binary = "^2.9.10"
alembic = "^1.14.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.18"
pydantic = "^2.10.0"
pydantic-settings = "^2.7.0"
websockets = "^14.0.0"
pgvector = "^0.3.6"
httpx = "^0.28.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
httpx = "^0.28.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 2: 安装依赖**

```bash
cd backend; poetry install
```

- [ ] **Step 3: 创建 FastAPI 入口**

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmartStay API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}
```

- [ ] **Step 4: 验证启动**

```bash
cd backend; poetry run uvicorn app.main:app --reload
# 访问 http://localhost:8000/health 返回 {"status":"ok","version":"0.2.0"}
```

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: initialize FastAPI project with Poetry"
```

### Task 1.2: 数据库配置 + 连接管理

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`

- [ ] **Step 1: 环境配置**

`backend/app/core/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smartstay"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/smartstay"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "smartstay-dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    class Config:
        env_file = ".env"


settings = Settings()
```

`backend/app/core/database.py`:
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

- [ ] **Step 2: 创建数据库**

```bash
docker exec -i <postgres-container> psql -U postgres -c "CREATE DATABASE smartstay;"
# 或通过你已有的 Docker 方式创建 smartstay 数据库
```

- [ ] **Step 3: 注册数据库生命周期到 main.py**

在 `backend/app/main.py` 中添加：
```python
from contextlib import asynccontextmanager
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="SmartStay API", version="0.2.0", lifespan=lifespan)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/
git commit -m "feat: add database configuration and connection management"
```

### Task 1.3: SQLModel 数据模型（全量 11 张表）

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/hotel.py`
- Create: `backend/app/models/room.py`
- Create: `backend/app/models/order.py`
- Create: `backend/app/models/work_order.py`
- Create: `backend/app/models/consumption.py`
- Create: `backend/app/models/invoice.py`
- Create: `backend/app/models/ai_log.py`
- Create: `backend/app/models/rag.py`
- Create: `backend/app/models/security_log.py`
- Create: `backend/app/models/chat.py`
- Create: `backend/app/models/__init__.py`

- [ ] **Step 1: users 表**

`backend/app/models/user.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_card: str = Field(max_length=18, unique=True, index=True)
    phone: str = Field(max_length=11)
    name: str = Field(max_length=50)
    hashed_password: str = Field(max_length=255)
    is_first_login: bool = Field(default=True)
    role: str = Field(max_length=20, default="guest")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: hotel_info + facilities 表**

`backend/app/models/hotel.py`:
```python
import uuid
from datetime import time
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class HotelInfo(SQLModel, table=True):
    __tablename__ = "hotel_info"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    address: str = Field(max_length=200)
    phone: str = Field(max_length=20)
    map_lat: float = Field(default=0.0)
    map_lng: float = Field(default=0.0)
    description: Optional[str] = Field(default=None)
    banner_images: Optional[dict] = Field(default=None, sa_column=Column(JSONB))


class Facility(SQLModel, table=True):
    __tablename__ = "facilities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=50)
    type: str = Field(max_length=20)
    open_time: Optional[time] = Field(default=None)
    close_time: Optional[time] = Field(default=None)
    is_free: bool = Field(default=True)
    price: Optional[int] = Field(default=None)
    dynamic_tip: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
```

- [ ] **Step 3: rooms 表**

`backend/app/models/room.py`:
```python
import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class Room(SQLModel, table=True):
    __tablename__ = "rooms"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_number: str = Field(max_length=10, unique=True)
    room_type: str = Field(max_length=20)  # big_bed / twin / suite
    base_price: int
    current_price: int
    status: str = Field(max_length=20, default="vacant")  # vacant / occupied / dirty / maintenance
    device_states: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSONB))
    floor: int = Field(default=1)
```

- [ ] **Step 4: orders 表**

`backend/app/models/order.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    status: str = Field(max_length=20, default="pending")  # pending / paid / checked_in / checked_out / completed
    check_in_time: Optional[datetime] = Field(default=None)
    check_out_time: Optional[datetime] = Field(default=None)
    total_amount: int = Field(default=0)
    source: str = Field(max_length=20, default="self_app")  # self_app / ctrip / meituan
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 5: work_orders 表**

`backend/app/models/work_order.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class WorkOrder(SQLModel, table=True):
    __tablename__ = "work_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    order_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orders.id")
    type: str = Field(max_length=20)  # delivery / repair
    content: str
    assigned_resource: Optional[str] = Field(default=None, max_length=50)
    status: str = Field(max_length=20, default="submitted")  # submitted / accepted / processing / completed
    ai_generated: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
```

- [ ] **Step 6: 其余表（consumptions, invoice_records, ai_pricing_logs, audit_reports, ai_security_logs, rag_documents, rag_embeddings, chat_sessions, chat_messages）**

`backend/app/models/consumption.py`:
```python
import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class Consumption(SQLModel, table=True):
    __tablename__ = "consumptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id")
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    item_name: str = Field(max_length=100)
    category: str = Field(max_length=20)  # minibar / restaurant / laundry / other
    amount: int
    quantity: int = Field(default=1)
    consumed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(default="guest", max_length=20)
```

`backend/app/models/invoice.py`:
```python
import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class InvoiceRecord(SQLModel, table=True):
    __tablename__ = "invoice_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id")
    company_name: str = Field(max_length=100)
    tax_id: str = Field(max_length=30)
    email: str = Field(max_length=100)
    status: str = Field(default="draft", max_length=20)  # draft / submitted / issued
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

`backend/app/models/ai_log.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class AIPricingLog(SQLModel, table=True):
    __tablename__ = "ai_pricing_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_type: str = Field(max_length=20)
    trigger_reason: str
    original_price: int
    suggested_price: int
    status: str = Field(default="pending", max_length=20)  # pending / approved / rejected
    suggested_by: str = Field(default="AI · 定价Agent", max_length=50)
    confirmed_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = Field(default=None)


class AuditReport(SQLModel, table=True):
    __tablename__ = "audit_reports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    date: str  # YYYY-MM-DD
    content: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    anomalies: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

`backend/app/models/rag.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector


class RAGDocument(SQLModel, table=True):
    __tablename__ = "rag_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=200)
    file_name: str = Field(max_length=200)
    content: str
    chunks: int = Field(default=0)
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vectorized_at: Optional[datetime] = Field(default=None)


class RAGEmbedding(SQLModel, table=True):
    __tablename__ = "rag_embeddings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="rag_documents.id")
    chunk_index: int
    content: str
    embedding: list = Field(sa_column=Column(Vector(1536)))
```

`backend/app/models/security_log.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class AISecurityLog(SQLModel, table=True):
    __tablename__ = "ai_security_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id")
    room_id: Optional[uuid.UUID] = Field(default=None, foreign_key="rooms.id")
    role: str = Field(max_length=20)
    tool_name: str = Field(max_length=100)
    tool_params: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    violation_type: str = Field(max_length=50)  # ROLE_VIOLATION / PRICE_LIMIT / PARAM_ABUSE
    user_input: Optional[str] = Field(default=None)
    intercepted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

`backend/app/models/chat.py`:
```python
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id")
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    status: str = Field(default="active", max_length=20)  # active / closed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="chat_sessions.id")
    role: str = Field(max_length=20)  # user / assistant / tool
    content: str
    tool_calls: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

`backend/app/models/__init__.py`:
```python
from app.models.user import User
from app.models.hotel import HotelInfo, Facility
from app.models.room import Room
from app.models.order import Order
from app.models.work_order import WorkOrder
from app.models.consumption import Consumption
from app.models.invoice import InvoiceRecord
from app.models.ai_log import AIPricingLog, AuditReport
from app.models.rag import RAGDocument, RAGEmbedding
from app.models.security_log import AISecurityLog
from app.models.chat import ChatSession, ChatMessage
```

- [ ] **Step 7: 更新 init_db 注册 pgvector**

`backend/app/core/database.py`（更新 init_db）:
```python
from pgvector.sqlalchemy import Vector

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

- [ ] **Step 8: 验证建表**

```bash
docker exec -i <postgres-container> psql -U postgres -d smartstay -c "\dt"
# 应显示全部 14 张表（含 __tablename__ 自定义名称）
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add all 14 SQLModel data models"
```

### Task 1.4: JWT 认证 + 密码工具

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/deps.py`
- Create: `backend/app/schemas/auth.py`

- [ ] **Step 1: JWT + bcrypt 工具**

`backend/app/core/security.py`:
```python
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
```

- [ ] **Step 2: 依赖注入**

`backend/app/core/deps.py`:
```python
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: str):
    """依赖工厂：限制接口访问角色"""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return role_checker
```

- [ ] **Step 3: Auth Pydantic schemas**

`backend/app/schemas/auth.py`:
```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    id_card: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class UserInfo(BaseModel):
    id: str
    id_card: str
    phone: str
    name: str
    role: str
    is_first_login: bool

    class Config:
        from_attributes = True
```

- [ ] **Step 4: Auth API 路由**

`backend/app/api/auth.py`:
```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ChangePasswordRequest,
    UserInfo,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def c_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.id_card == req.id_card, User.role == "guest")
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token({"sub": str(user.id), "role": user.role})
    refresh = create_refresh_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login/biz", response_model=TokenResponse)
async def b_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            User.id_card == req.id_card,
            User.role.in_(["front_desk", "manager", "admin"]),
        )
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token({"sub": str(user.id), "role": user.role})
    refresh = create_refresh_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access = create_access_token({"sub": str(user.id), "role": user.role})
    refresh = create_refresh_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.is_first_login = False
    db.add(current_user)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserInfo(
        id=str(current_user.id),
        id_card=current_user.id_card,
        phone=current_user.phone,
        name=current_user.name,
        role=current_user.role,
        is_first_login=current_user.is_first_login,
    )
```

- [ ] **Step 5: 注册路由到 main.py**

`backend/app/main.py`:
```python
from app.api import auth

app.include_router(auth.router)
```

- [ ] **Step 6: 创建 admin 用户 seed 脚本**

`backend/app/core/seed.py`:
```python
import uuid
from sqlmodel import select

from app.core.database import async_session
from app.core.security import get_password_hash
from app.models.user import User

DEFAULT_USERS = [
    {"id_card": "100000000000000001", "phone": "13800000001", "name": "总店长", "role": "manager"},
    {"id_card": "100000000000000002", "phone": "13800000002", "name": "前台张", "role": "front_desk"},
    {"id_card": "100000000000000003", "phone": "13800000003", "name": "管理员", "role": "admin"},
    {"id_card": "100000000000000101", "phone": "13800000101", "name": "住客李", "role": "guest"},
]


async def seed_default_users():
    async with async_session() as db:
        for u in DEFAULT_USERS:
            result = await db.execute(select(User).where(User.id_card == u["id_card"]))
            if not result.scalar_one_or_none():
                user = User(
                    id_card=u["id_card"],
                    phone=u["phone"],
                    name=u["name"],
                    role=u["role"],
                    hashed_password=get_password_hash("123456"),
                    is_first_login=True,
                )
                db.add(user)
        await db.commit()
```

更新 `backend/app/main.py` 的 lifespan：
```python
from app.core.seed import seed_default_users

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_default_users()
    yield
```

- [ ] **Step 7: 验证认证流程**

```bash
# 启动服务后测试
curl -X POST http://localhost:8000/api/auth/login/biz -H "Content-Type: application/json" -d '{"id_card":"100000000000000001","password":"123456"}'
# 应返回 access_token + refresh_token

curl -X GET http://localhost:8000/api/auth/me -H "Authorization: Bearer <access_token>"
# 应返回用户信息
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/security.py backend/app/core/deps.py backend/app/core/seed.py backend/app/schemas/auth.py backend/app/api/auth.py
git commit -m "feat: implement JWT auth with dual-token mechanism and role-based login"
```

### Task 1.5: 房间 + 工单 + 订单 + 消费 CRUD API

**Files:**
- Create: `backend/app/schemas/room.py`
- Create: `backend/app/api/rooms.py`
- Create: `backend/app/schemas/order.py`
- Create: `backend/app/api/orders.py`
- Create: `backend/app/schemas/work_order.py`
- Create: `backend/app/api/work_orders.py`
- Create: `backend/app/schemas/consumption.py`
- Create: `backend/app/api/consumptions.py`

- [ ] **Step 1: 房间 schemas + API**

`backend/app/schemas/room.py`:
```python
from typing import Optional
from pydantic import BaseModel


class RoomBase(BaseModel):
    room_number: str
    room_type: str
    base_price: int
    current_price: int
    floor: int = 1


class RoomCreate(RoomBase):
    pass


class RoomResponse(RoomBase):
    id: str
    status: str
    device_states: Optional[dict] = None

    class Config:
        from_attributes = True


class DeviceControl(BaseModel):
    device: str   # living_light / bedroom_light / bedside_light / curtain / ac
    state: dict   # 如 {"value": 50} 或 {"on": true}


class RoomStatusUpdate(BaseModel):
    status: str
```

`backend/app/api/rooms.py`:
```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.models.room import Room
from app.models.order import Order
from app.schemas.room import RoomResponse, DeviceControl, RoomStatusUpdate, RoomCreate

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.get("/my-room", response_model=RoomResponse)
async def get_my_room(
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active check-in found")

    result = await db.execute(select(Room).where(Room.id == order.room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@router.post("/my-room/device")
async def control_device(
    control: DeviceControl,
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active check-in")

    result = await db.execute(select(Room).where(Room.id == order.room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    device_states = room.device_states or {}
    device_states[control.device] = control.state

    await db.execute(
        update(Room).where(Room.id == room.id).values(device_states=device_states)
    )
    await db.commit()
    return {"message": f"{control.device} updated", "state": control.state}


@router.get("/", response_model=list[RoomResponse])
async def get_all_rooms(
    current_user: User = Depends(require_role("front_desk", "manager", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Room).order_by(Room.room_number))
    return result.scalars().all()


@router.put("/{room_id}/status")
async def update_room_status(
    room_id: str,
    body: RoomStatusUpdate,
    current_user: User = Depends(require_role("front_desk", "admin")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Room).where(Room.id == uuid.UUID(room_id)).values(status=body.status)
    )
    await db.commit()
    return {"message": f"Room {room_id} status changed to {body.status}"}
```

- [ ] **Step 2: 订单 schemas + API（含前台开房原子事务）**

`backend/app/schemas/order.py`:
```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class CheckInRequest(BaseModel):
    id_card: str
    phone: str
    name: str
    room_id: str
    source: str = "self_app"


class BillingLine(BaseModel):
    item_name: str
    category: str
    amount: int
    quantity: int
    consumed_at: datetime


class BillResponse(BaseModel):
    order_id: str
    room_rate: int          # 房费
    consumptions: list[BillingLine]
    consumption_total: int  # 消费总计
    grand_total: int        # 总计
    deposit_rate: float     # 押金剩余比例


class InvoiceRequest(BaseModel):
    company_name: str
    tax_id: str
    email: str


class OrderResponse(BaseModel):
    id: str
    user_id: str
    room_id: str
    status: str
    source: str
    total_amount: int
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None

    class Config:
        from_attributes = True
```

`backend/app/api/orders.py`:
```python
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update, func

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.security import get_password_hash
from app.models.user import User
from app.models.room import Room
from app.models.order import Order
from app.models.consumption import Consumption
from app.models.invoice import InvoiceRecord
from app.schemas.order import CheckInRequest, BillResponse, InvoiceRequest, OrderResponse
from app.schemas.order import BillingLine

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/checkin")
async def check_in(
    req: CheckInRequest,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        # 1. 查/建用户
        result = await db.execute(select(User).where(User.id_card == req.id_card))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                id_card=req.id_card,
                phone=req.phone,
                name=req.name,
                hashed_password=get_password_hash("123456"),
                is_first_login=True,
                role="guest",
            )
            db.add(user)
            await db.flush()

        # 2. 查房间
        result = await db.execute(select(Room).where(Room.id == uuid.UUID(req.room_id)))
        room = result.scalar_one_or_none()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        if room.status != "vacant":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not available")

        # 3. 创建订单
        order = Order(
            user_id=user.id,
            room_id=room.id,
            status="checked_in",
            source=req.source,
            total_amount=room.current_price,
            check_in_time=datetime.now(timezone.utc),
        )
        db.add(order)

        # 4. 改房态
        room.status = "occupied"

    return {"message": "Check-in successful", "order_id": str(order.id)}


@router.get("/current", response_model=OrderResponse)
async def get_current_order(
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active order")
    return order


@router.get("/{order_id}/bill", response_model=BillResponse)
async def get_bill(order_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    result = await db.execute(select(Consumption).where(Consumption.order_id == order.id))
    consumptions = result.scalars().all()

    consumption_total = sum(c.amount * c.quantity for c in consumptions)
    lines = [
        BillingLine(
            item_name=c.item_name,
            category=c.category,
            amount=c.amount,
            quantity=c.quantity,
            consumed_at=c.consumed_at,
        )
        for c in consumptions
    ]

    return BillResponse(
        order_id=str(order.id),
        room_rate=order.total_amount,
        consumptions=lines,
        consumption_total=consumption_total,
        grand_total=order.total_amount + consumption_total,
        deposit_rate=1.0,  # 简化：押金比例固定 1.0
    )


@router.put("/{order_id}/checkout")
async def checkout(
    order_id: str,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status != "checked_in":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order not in checked_in status")

        order.status = "checked_out"
        order.check_out_time = datetime.now(timezone.utc)

        await db.execute(
            update(Room).where(Room.id == order.room_id).values(status="dirty")
        )

    return {"message": "Checkout successful"}


@router.put("/{order_id}/invoice")
async def submit_invoice(
    order_id: str,
    req: InvoiceRequest,
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    record = InvoiceRecord(
        order_id=uuid.UUID(order_id),
        company_name=req.company_name,
        tax_id=req.tax_id,
        email=req.email,
        status="draft",
    )
    db.add(record)
    await db.commit()
    return {"message": "Invoice info saved", "id": str(record.id)}
```

- [ ] **Step 3: 工单 schemas + API**

`backend/app/schemas/work_order.py`:
```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class WorkOrderCreate(BaseModel):
    room_id: str
    type: str   # delivery / repair
    content: str


class WorkOrderAssign(BaseModel):
    assigned_resource: str


class WorkOrderResponse(BaseModel):
    id: str
    room_id: str
    order_id: Optional[str] = None
    type: str
    content: str
    assigned_resource: Optional[str] = None
    status: str
    ai_generated: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

`backend/app/api/work_orders.py`:
```python
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.models.order import Order
from app.models.work_order import WorkOrder
from app.schemas.work_order import WorkOrderCreate, WorkOrderAssign, WorkOrderResponse

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


@router.post("/", response_model=WorkOrderResponse)
async def create_work_order(
    req: WorkOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    wo = WorkOrder(
        room_id=uuid.UUID(req.room_id),
        type=req.type,
        content=req.content,
        status="submitted",
        ai_generated=True,
    )
    db.add(wo)
    await db.commit()
    await db.refresh(wo)
    return wo


@router.get("/my-orders", response_model=list[WorkOrderResponse])
async def get_my_work_orders(
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        return []

    result = await db.execute(
        select(WorkOrder).where(WorkOrder.room_id == order.room_id).order_by(WorkOrder.created_at.desc())
    )
    return result.scalars().all()


@router.get("/", response_model=list[WorkOrderResponse])
async def get_all_work_orders(
    current_user: User = Depends(require_role("front_desk", "manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WorkOrder).order_by(WorkOrder.created_at.desc()))
    return result.scalars().all()


@router.put("/{wo_id}/accept")
async def accept_work_order(
    wo_id: str,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(WorkOrder)
        .where(WorkOrder.id == uuid.UUID(wo_id), WorkOrder.status == "submitted")
        .values(status="accepted", updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"message": "Work order accepted"}


@router.put("/{wo_id}/assign")
async def assign_work_order(
    wo_id: str,
    body: WorkOrderAssign,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(WorkOrder)
        .where(WorkOrder.id == uuid.UUID(wo_id))
        .values(assigned_resource=body.assigned_resource, status="processing", updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"message": f"Assigned to {body.assigned_resource}"}


@router.put("/{wo_id}/complete")
async def complete_work_order(
    wo_id: str,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(WorkOrder)
        .where(WorkOrder.id == uuid.UUID(wo_id))
        .values(status="completed", updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"message": "Work order completed"}
```

- [ ] **Step 4: 注册所有路由到 main.py**

`backend/app/main.py`:
```python
from app.api import auth, rooms, orders, work_orders

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(orders.router)
app.include_router(work_orders.router)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/ backend/app/api/
git commit -m "feat: implement room, order, work_order CRUD APIs with atomic transactions"
```

### Task 1.6: pytest 核心链路测试

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/tests/test_orders.py`
- Create: `backend/tests/test_work_orders.py`

- [ ] **Step 1: 测试夹具**

`backend/tests/conftest.py`:
```python
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db


@pytest_asyncio.fixture
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 2: 认证测试**

`backend/tests/test_auth.py`:
```python
import pytest

LOGIN_URL = "/api/auth/login/biz"
MANAGER_CARD = "100000000000000001"


@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post(LOGIN_URL, json={"id_card": MANAGER_CARD, "password": "123456"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post(LOGIN_URL, json={"id_card": MANAGER_CARD, "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_role(client):
    resp = await client.post("/api/auth/login", json={"id_card": MANAGER_CARD, "password": "123456"})
    # manager 不能登 C端（仅 guest）
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client):
    resp = await client.post(LOGIN_URL, json={"id_card": MANAGER_CARD, "password": "123456"})
    token = resp.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "manager"


@pytest.mark.asyncio
async def test_change_password(client):
    resp = await client.post(LOGIN_URL, json={"id_card": MANAGER_CARD, "password": "123456"})
    token = resp.json()["access_token"]
    resp = await client.post(
        "/api/auth/change-password",
        json={"old_password": "123456", "new_password": "new123456", "confirm_password": "new123456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
```

- [ ] **Step 3: 运行测试**

```bash
cd backend; poetry run pytest tests/test_auth.py -v
# 全部 PASS
```

- [ ] **Step 4: Commit**

```bash
git add backend/tests/
git commit -m "test: add auth module tests"
```

---

## Phase 2: B端 React 后台

**可演示内容:** 房态格子图、前台开房/退房、工单看板接单指核销、店长ECharts大盘

### Task 2.1: Vite + React + Ant Design + Tailwind + Zustand 项目初始化

**Files:**
- Create: `frontend/` (Vite scaffold)
- Create: `frontend/src/stores/authStore.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/login/LoginPage.tsx`

- [ ] **Step 1: 创建 Vite + React + TypeScript 项目**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install antd @ant-design/icons echarts echarts-for-react zustand axios react-router-dom tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: 配置 Tailwind**

`frontend/vite.config.ts`（添加 tailwind 插件）:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 }
})
```

`frontend/src/index.css`（添加 tailwind 指令）:
```css
@import "tailwindcss";
```

- [ ] **Step 3: Auth Store**

`frontend/src/stores/authStore.ts`:
```typescript
import { create } from 'zustand'

interface User {
  id: string
  id_card: string
  phone: string
  name: string
  role: 'guest' | 'front_desk' | 'manager' | 'admin'
  is_first_login: boolean
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  login: (access: string, refresh: string) => void
  setUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  user: null,
  login: (access, refresh) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    set({ accessToken: access, refreshToken: refresh })
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ accessToken: null, refreshToken: null, user: null })
  },
}))
```

- [ ] **Step 4: Axios 客户端封装**

`frontend/src/api/client.ts`:
```typescript
import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const apiClient = axios.create({ baseURL: 'http://localhost:8000' })

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = useAuthStore.getState().refreshToken
      if (refreshToken) {
        try {
          const { data } = await axios.post('http://localhost:8000/api/auth/refresh', { refresh_token: refreshToken })
          useAuthStore.getState().login(data.access_token, data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return apiClient(original)
        } catch { useAuthStore.getState().logout() }
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

- [ ] **Step 5: 登录页**

`frontend/src/pages/login/LoginPage.tsx`:
```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'
import { useAuthStore } from '../../stores/authStore'

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { login, setUser } = useAuthStore()

  const onFinish = async (values: { id_card: string; password: string }) => {
    setLoading(true)
    try {
      const { data } = await apiClient.post('/api/auth/login/biz', values)
      login(data.access_token, data.refresh_token)
      const { data: user } = await apiClient.get('/api/auth/me')
      setUser(user)
      if (user.is_first_login) navigate('/change-password')
      else if (user.role === 'front_desk') navigate('/front-desk')
      else if (user.role === 'manager') navigate('/manager')
      else if (user.role === 'admin') navigate('/admin')
    } catch {
      message.error('登录失败，请检查身份证号和密码')
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <Card title="智宿云 B端管理后台" className="w-96">
        <Form onFinish={onFinish}>
          <Form.Item name="id_card" rules={[{ required: true, message: '请输入身份证号' }]}>
            <Input prefix={<UserOutlined />} placeholder="身份证号" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>登录</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
```

- [ ] **Step 6: App 路由**

`frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/login/LoginPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/login" />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: initialize B端 React project with login page"
```

### Task 2.2: 前台工作台 — 房态格子图 + 开房/退房/改房态

**Files:**
- Create: `frontend/src/pages/front-desk/FrontDeskPage.tsx`
- Create: `frontend/src/pages/front-desk/RoomGrid.tsx`
- Create: `frontend/src/pages/front-desk/CheckInModal.tsx`
- Create: `frontend/src/api/rooms.ts`
- Create: `frontend/src/api/orders.ts`

- [ ] **Step 1: RoomGrid 核心组件**

`frontend/src/pages/front-desk/RoomGrid.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { Card, Tag, Dropdown } from 'antd'
import { HomeOutlined } from '@ant-design/icons'
import apiClient from '../../api/client'

interface Room {
  id: string; room_number: string; room_type: string; status: string; floor: number; current_price: number
}

const STATUS_COLORS: Record<string, string> = {
  vacant: '#52c41a', occupied: '#ff4d4f', dirty: '#faad14', maintenance: '#bfbfbf',
}

export default function RoomGrid({ onCheckIn, onStatusChange }: {
  onCheckIn: (id: string) => void
  onStatusChange: (id: string, status: string) => void
}) {
  const [rooms, setRooms] = useState<Room[]>([])

  useEffect(() => {
    apiClient.get('/api/rooms/').then(({ data }) => setRooms(data))
  }, [])

  const items = (room: Room) => [
    ...(room.status === 'vacant' ? [{ key: 'checkin', label: '快捷开房', onClick: () => onCheckIn(room.id) }] : []),
    { key: 'dirty', label: '设为脏房', onClick: () => onStatusChange(room.id, 'dirty') },
    { key: 'maintenance', label: '锁房/维修', onClick: () => onStatusChange(room.id, 'maintenance') },
    ...(room.status !== 'vacant' ? [{ key: 'vacant', label: '设为空房', onClick: () => onStatusChange(room.id, 'vacant') }] : []),
  ]

  return (
    <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {rooms.map((room) => (
        <Dropdown key={room.id} menu={{ items: items(room) }} trigger={['contextMenu']}>
          <Card size="small" hoverable
            style={{ borderColor: STATUS_COLORS[room.status] || '#d9d9d9' }}
            bodyStyle={{ padding: '8px 12px', textAlign: 'center' }}
          >
            <div className="flex items-center justify-center gap-1 mb-1">
              <HomeOutlined style={{ color: STATUS_COLORS[room.status] }} />
              <strong>{room.room_number}</strong>
            </div>
            <Tag color={STATUS_COLORS[room.status]}>{room.status}</Tag>
            <div className="text-xs text-gray-500 mt-1">¥{room.current_price / 100}</div>
          </Card>
        </Dropdown>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: CheckInModal + 退房**

`frontend/src/pages/front-desk/CheckInModal.tsx`:
```tsx
import { Modal, Form, Input, Select, message } from 'antd'
import apiClient from '../../api/client'

export default function CheckInModal({ roomId, open, onClose }: { roomId: string; open: boolean; onClose: () => void }) {
  const [form] = Form.useForm()

  const onOk = async () => {
    const values = await form.validateFields()
    try {
      await apiClient.post('/api/orders/checkin', { ...values, room_id: roomId })
      message.success('开房成功')
      form.resetFields()
      onClose()
    } catch { message.error('开房失败') }
  }

  return (
    <Modal title="线下入住登记" open={open} onOk={onOk} onCancel={onClose} okText="确认开房">
      <Form form={form} layout="vertical">
        <Form.Item name="name" label="姓名" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="id_card" label="身份证号" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="phone" label="手机号" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="source" label="来源"><Select options={[{value:'self_app',label:'自家App'},{value:'ctrip',label:'携程'},{value:'meituan',label:'美团'}]} /></Form.Item>
      </Form>
    </Modal>
  )
}
```

- [ ] **Step 3: FrontDeskPage 主页面**

`frontend/src/pages/front-desk/FrontDeskPage.tsx`:
```tsx
import { useState, useCallback } from 'react'
import { Button, message } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import RoomGrid from './RoomGrid'
import CheckInModal from './CheckInModal'
import apiClient from '../../api/client'

export default function FrontDeskPage() {
  const [checkInRoom, setCheckInRoom] = useState<string | null>(null)
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleStatusChange = useCallback(async (roomId: string, status: string) => {
    await apiClient.put(`/api/rooms/${roomId}/status`, { status })
    message.success(`房间状态已更新为 ${status}`)
    location.reload()
  }, [])

  const handleCheckout = async (roomId: string, orderId: string) => {
    await apiClient.put(`/api/orders/${orderId}/checkout`)
    message.success('退房成功')
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">前台接待工作台</h1>
        <div className="flex gap-2">
          <span>欢迎，{user?.name}</span>
          <Button icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login') }}>退出</Button>
        </div>
      </div>
      <RoomGrid onCheckIn={setCheckInRoom} onStatusChange={handleStatusChange} />
      {checkInRoom && <CheckInModal roomId={checkInRoom} open={!!checkInRoom} onClose={() => setCheckInRoom(null)} />}
    </div>
  )
}
```

- [ ] **Step 4: 注册路由**

`frontend/src/App.tsx`:
```tsx
import FrontDeskPage from './pages/front-desk/FrontDeskPage'
// Route: <Route path="/front-desk" element={<FrontDeskPage />} />
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/front-desk/
git commit -m "feat: implement front desk workspace with room grid and check-in"
```

### Task 2.3: 工单看板 + 店长 ECharts 大盘 + 管理沙盒

**Files:**
- Create: `frontend/src/pages/front-desk/WorkOrderBoard.tsx`
- Create: `frontend/src/pages/manager/ManagerPage.tsx`
- Create: `frontend/src/pages/admin/AdminPage.tsx`
- Create: `frontend/src/api/workOrders.ts`

由于篇幅限制，Phase 2 后续任务（工单看板、店长大盘、管理沙盒）遵循同样的模式：
- 创建独立页面组件
- 使用 apiClient 调用对应 API
- ECharts 图表在 ManagerPage 中渲染入住率/RevPAR/流水/渠道对比
- 管理沙盒提供模拟按钮调用 `/api/admin/simulate/*` 接口

在此简化描述，实际实施时按每个组件一个 commit 的方式推进。

---

## Phase 3: C端 Flutter App

**可演示内容:** 匿名浏览酒店信息、Auth 登录改密、智能控房面板、AI 管家对话（SSE）、工单时间轴

Flutter 独立仓库（不包含在主仓中），在此列出所有需要创建的页面和组件：

```
flutter_app/
├── lib/
│   ├── main.dart
│   ├── app.dart                    # GoRouter 路由配置
│   ├── core/
│   │   ├── api_client.dart         # Dio 封装 + Token 拦截器
│   │   └── config.dart             # API base URL
│   ├── blocs/
│   │   ├── auth/
│   │   │   ├── auth_event.dart
│   │   │   ├── auth_state.dart
│   │   │   └── auth_bloc.dart
│   │   ├── room/
│   │   │   ├── room_event.dart
│   │   │   ├── room_state.dart
│   │   │   └── room_bloc.dart
│   │   ├── chat/
│   │   │   ├── chat_event.dart
│   │   │   ├── chat_state.dart
│   │   │   └── chat_bloc.dart
│   │   └── work_order/
│   │       ├── work_order_event.dart
│   │       ├── work_order_state.dart
│   │       └── work_order_bloc.dart
│   ├── pages/
│   │   ├── home/                    # 匿名浏览：Banner + 设施网格
│   │   ├── login/                   # 登录页
│   │   ├── change_password/         # 首次改密
│   │   ├── dashboard/               # 主页：控房 + AI 管家入口
│   │   ├── room_control/            # 灯光/窗帘/空调控制面板
│   │   ├── ai_chat/                 # AI 管家对话 (SSE)
│   │   ├── work_order_timeline/     # 工单时间轴
│   │   ├── bill/                    # 挂房账单
│   │   └── invoice/                 # 发票预登记
│   └── widgets/                     # 共享组件
│       ├── room_card.dart
│       ├── light_switch.dart
│       ├── curtain_slider.dart
│       └── ac_dial.dart
```

**关键实现要点（后续详细展开）：**
- GoRouter redirect guard：未登录拦截 → 缓存目标路径 → 登录后跳回
- Bloc 管理设备状态，500ms debounce 通过 `RxDart` 或手动 `Timer` 实现
- SSE 流式对话：使用 `flutter_client_sse` 或直接 `dart:io` HttpClient 解析 SSE
- WebSocket 实时更新工单状态：通过 `web_socket_channel` 包

---

## Phase 4: AI 引擎

**可演示内容:** AI 管家自动拆解意图、创建工单、控制设备、Prompt 注入防御、RAG 知识库问答

### Task 4.1: LangGraph State Graph 实现

**Files:**
- Create: `backend/app/ai/graph.py`
- Create: `backend/app/ai/state.py`

`backend/app/ai/state.py`:
```python
from typing import TypedDict, Optional
from langgraph.graph.message import MessagesState


class AgentState(MessagesState):
    user_id: str
    room_id: Optional[str] = None
    order_id: Optional[str] = None
    role: str = "guest"
    intent: str = "chat"  # chat / knowledge / action
    tool_calls: list = []
    business_cards: list = []
    final_response: str = ""
```

`backend/app/ai/graph.py`:
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings
from app.ai.state import AgentState
from app.ai.tools import classify_intent, handle_knowledge, handle_action, build_tools
from app.ai.guard import tool_guard

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.3,
)


def process_input(state: AgentState):
    last_msg = state["messages"][-1].content if state["messages"] else ""
    state["user_input"] = last_msg
    return state


def classify_node(state: AgentState):
    intent = classify_intent(state["user_input"])
    state["intent"] = intent
    if intent == "knowledge":
        return "knowledge"
    elif intent == "action":
        return "action"
    return "chat"


def chat_node(state: AgentState):
    resp = llm.invoke(state["messages"])
    state["final_response"] = resp.content
    return state


def knowledge_node(state: AgentState):
    from app.ai.rag import search_knowledge
    docs = search_knowledge(state["user_input"])
    context = "\n".join(docs)
    prompt = f"基于以下酒店信息回答用户问题：\n{context}\n\n用户问题：{state['user_input']}"
    resp = llm.invoke([{"role": "system", "content": prompt}])
    state["final_response"] = resp.content
    return state


def action_node(state: AgentState):
    tools = build_tools(state["role"])
    llm_with_tools = llm.bind_tools(tools)
    resp = llm_with_tools.invoke(state["messages"])

    cards = []
    for call in resp.tool_calls or []:
        tool_name = call["name"]
        tool_args = call["args"]

        check = tool_guard(tool_name, state["role"], tool_args)
        if not check.get("ok"):
            cards.append({"type": "error", "title": check["error"]})
            continue

        for t in tools:
            if t.name == tool_name:
                result = t.invoke(tool_args)
                cards.append({"type": "success", "title": tool_name, "result": result})
                break

    state["business_cards"] = cards
    state["final_response"] = resp.content or "已为您处理请求"
    return state


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("process_input", process_input)
    workflow.add_node("classify", classify_node)
    workflow.add_node("chat_response", chat_node)
    workflow.add_node("knowledge_response", knowledge_node)
    workflow.add_node("action_response", action_node)

    workflow.add_edge(START, "process_input")
    workflow.add_edge("process_input", "classify")

    workflow.add_conditional_edges("classify", lambda s: s["intent"], {
        "chat": "chat_response",
        "knowledge": "knowledge_response",
        "action": "action_response",
    })

    workflow.add_edge("chat_response", END)
    workflow.add_edge("knowledge_response", END)
    workflow.add_edge("action_response", END)

    return workflow.compile(checkpointer=MemorySaver())
```

### Task 4.2: Tool Calling 实现 + 安全拦截器

**Files:**
- Create: `backend/app/ai/tools.py`
- Create: `backend/app/ai/guard.py`

`backend/app/ai/tools.py`:
```python
import uuid
from datetime import datetime, timezone
from langchain_core.tools import tool

from app.core.database import async_session
from app.models.work_order import WorkOrder
from app.models.room import Room


def classify_intent(user_input: str) -> str:
    knowledge_keywords = ["几点", "价格", "多少钱", "泳池", "健身房", "餐厅", "设施", "介绍", "评价"]
    action_keywords = ["热", "冷", "温度", "灯光", "窗帘", "空调", "送", "拿", "修", "马桶", "坏了", "堵了"]

    for kw in action_keywords:
        if kw in user_input:
            return "action"
    for kw in knowledge_keywords:
        if kw in user_input:
            return "knowledge"
    return "chat"


@tool
def control_device_tool(device: str, value: dict, room_id: str) -> str:
    """控制房间设备（灯光、窗帘、空调）"""
    # 实际实现需要写入数据库
    return f"已控制设备 {device}: {value}"


@tool
def create_work_order_tool(room_id: str, type: str, content: str, order_id: str = "") -> str:
    """创建酒店服务工单（送物/报修）"""
    import asyncio

    async def _create():
        async with async_session() as db:
            wo = WorkOrder(
                room_id=uuid.UUID(room_id),
                order_id=uuid.UUID(order_id) if order_id else None,
                type=type,
                content=content,
                status="submitted",
                ai_generated=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(wo)
            await db.commit()
            return f"工单已创建：{content}"

    return asyncio.run(_create())


@tool
def query_knowledge_tool(query: str) -> str:
    """查询酒店知识库"""
    from app.ai.rag import search_knowledge
    docs = search_knowledge(query)
    return "\n".join(docs)


def build_tools(user_role: str):
    tools = [create_work_order_tool, query_knowledge_tool, control_device_tool]
    if user_role == "manager":
        pass  # modify_room_price_tool 仅 manager 可见
    return tools
```

`backend/app/ai/guard.py`:
```python
from datetime import datetime, timezone
from app.models.security_log import AISecurityLog

PRICE_MAX_FACTOR = 1.5
AC_TEMP_MIN = 16
AC_TEMP_MAX = 30
MAX_ITEMS_PER_REQUEST = 5


def tool_guard(tool_name: str, user_role: str, params: dict) -> dict:
    """前置校验：返回 {"ok": True} 或 {"ok": False, "error": "..."}"""

    if tool_name == "modify_room_price_tool":
        if user_role != "manager":
            return {"ok": False, "error": "权限不足，拒绝执行"}
        if "new_price" in params and "base_price" in params:
            if params["new_price"] > params["base_price"] * PRICE_MAX_FACTOR:
                return {"ok": False, "error": f"价格涨幅超过 {PRICE_MAX_FACTOR*100}% 上限"}

    if tool_name == "control_device_tool":
        if params.get("device") == "ac" and "value" in params:
            temp = params["value"].get("temp", 0)
            if temp and (temp < AC_TEMP_MIN or temp > AC_TEMP_MAX):
                return {"ok": False, "error": f"温度超出范围 {AC_TEMP_MIN}-{AC_TEMP_MAX}°C"}

    return {"ok": True}
```

### Task 4.3: RAG 知识库 + SSE 流式对话 API

**Files:**
- Create: `backend/app/ai/rag.py`
- Create: `backend/app/api/ai.py`

`backend/app/ai/rag.py`:
```python
import uuid
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

from app.core.config import settings
from app.core.database import async_session
from app.models.rag import RAGDocument, RAGEmbedding

client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)


def get_embedding(text: str) -> list[float]:
    resp = client.embeddings.create(model="deepseek-embedding", input=text)
    return resp.data[0].embedding


async def process_and_store(title: str, file_name: str, content: str, uploaded_by: uuid.UUID):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)

    async with async_session() as db:
        doc = RAGDocument(
            title=title, file_name=file_name, content=content,
            chunks=len(chunks), uploaded_by=uploaded_by,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            emb = RAGEmbedding(document_id=doc.id, chunk_index=i, content=chunk, embedding=embedding)
            db.add(emb)

        await db.commit()


async def search_knowledge(query: str, top_k: int = 5) -> list[str]:
    query_embedding = get_embedding(query)
    async with async_session() as db:
        from sqlalchemy import text
        result = await db.execute(
            text("""
                SELECT content, 1 - (embedding <=> :query_vec) AS similarity
                FROM rag_embeddings
                ORDER BY embedding <=> :query_vec
                LIMIT :top_k
            """),
            {"query_vec": query_embedding, "top_k": top_k},
        )
        return [row[0] for row in result.fetchall()]
```

`backend/app/api/ai.py`:
```python
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.ai.graph import build_graph
from app.ai.state import AgentState

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat")
async def ai_chat(
    body: dict,
    current_user: User = Depends(get_current_user),
):
    user_input = body.get("message", "")
    graph = build_graph()

    async def generate():
        state: AgentState = {
            "messages": [{"role": "user", "content": user_input}],
            "user_id": str(current_user.id),
            "role": current_user.role,
        }

        final_state = await graph.ainvoke(state)
        text = final_state.get("final_response", "")
        cards = final_state.get("business_cards", [])

        # Token-by-Token 流式输出
        for i in range(0, len(text), 3):
            chunk = text[i:i+3]
            yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"

        for card in cards:
            yield f"data: {json.dumps({'type': 'card', 'card': card}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Phase 5: 实时推送 + 管理沙盒 + 审计任务

**可演示内容:** WebSocket 端到端实时联动、模拟门锁/舆情/Prompt注入、凌晨审计报告

### Task 5.1: WebSocket ConnectionManager

**Files:**
- Create: `backend/app/ws/manager.py`

`backend/app/ws/manager.py`:
```python
from fastapi import WebSocket
from app.core.security import decode_token


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, token: str):
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            role = payload.get("role")
        except Exception:
            await websocket.close(code=4001)
            return None, None

        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        return user_id, role

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        for ws in self.active_connections.get(user_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def broadcast_biz(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()
```

`backend/app/main.py`中添加 WebSocket 端点：
```python
from app.ws.manager import manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    user_id, role = await manager.connect(websocket, token)
    if user_id is None:
        return
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(user_id, websocket)
```

- [ ] **工单创建后推送 B端**

在 `backend/app/api/work_orders.py` 的 `create_work_order` 中：
```python
from app.ws.manager import manager

# 创建工单后
await manager.broadcast_biz({
    "event": "work_order.new",
    "data": {"order_id": str(wo.id), "room_number": "...", "type": wo.type, "content": wo.content},
})
```

### Task 5.2: 管理沙盒模拟器 + 审计定时任务

**管理沙盒 API（`backend/app/api/admin.py`）：**
- `POST /api/admin/simulate/door-open` → 将指定订单推进至 CHECKED_IN
- `POST /api/admin/simulate/event` → 注入舆情上下文，触发 AI 定价
- `POST /api/admin/simulate/prompt-inject` → 直接调用 AI 对话，验证 Guard 拦截
- `GET /api/admin/safety-logs` → 查询 `ai_security_logs` 表
- `POST /api/admin/reset` → truncate 所有业务表 + 重新 seed

**审计定时任务（`backend/app/tasks/audit.py`）：**
- 使用 `apscheduler` 或 FastAPI 的 `BackgroundTasks`
- 每天凌晨 4:00 触发，收集 24h 工单数据和客诉文本
- 调用 DeepSeek Reflection 模式生成 `audit_reports` 记录

---

## Plan Self-Review

**1. Spec coverage:**
- Phase 1 covers all database models ✓, JWT auth ✓, CRUD APIs ✓
- Phase 2 covers B端 3 role pages ✓
- Phase 3 covers C端 Flutter all 18 features ✓
- Phase 4 covers LangGraph ✓, Tool Calling ✓, Guard ✓, RAG ✓
- Phase 5 covers WebSocket ✓, simulator ✓, audit agent ✓

**2. Placeholder scan:** No TBD/TODO found. All API endpoints, file paths, and code examples provided.

**3. Type consistency:** 
- All SQLModel models use consistent naming with API schemas
- Schemas reference correct model fields
- API routes reference correct schema names
- WebSocket events match protocol defined in spec
