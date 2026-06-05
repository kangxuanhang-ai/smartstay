from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    import app.models  # noqa: F401 - triggers model registration with SQLModel.metadata
    import pgvector.sqlalchemy  # noqa: F401
    from sqlalchemy import text

    # Step 1: 启用 pgvector 扩展 + 创建所有表
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.create_all)

    # Step 2: 迁移（表已存在，单独事务，失败不影响其他）
    async with engine.begin() as conn:
        for stmt in [
            "ALTER TABLE guests ADD COLUMN IF NOT EXISTS face_id VARCHAR(64)",
            "ALTER TABLE guests ADD COLUMN IF NOT EXISTS face_registered BOOLEAN DEFAULT FALSE",
            "ALTER TABLE ai_security_logs ADD COLUMN IF NOT EXISTS user_type VARCHAR(20) DEFAULT 'guest'",
            "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS summary TEXT",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass

        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS guest_preferences (
                    id UUID PRIMARY KEY,
                    guest_id UUID NOT NULL REFERENCES guests(id),
                    key VARCHAR(50) NOT NULL,
                    value VARCHAR(20) NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(guest_id, key)
                )
            """))
        except Exception:
            pass
