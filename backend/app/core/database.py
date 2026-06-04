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

    async with engine.begin() as conn:
        # 启用 pgvector 扩展
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # 迁移：rag_embeddings 表向量维度从 1536 改为 384，需要重建
        try:
            await conn.execute(text("DROP TABLE IF EXISTS rag_embeddings CASCADE"))
        except Exception:
            pass

        # 迁移：users 表拆分为 guests + staff
        try:
            await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        except Exception:
            pass

        # 迁移：guests 表新增 face_id + face_registered
        try:
            await conn.execute(text("ALTER TABLE guests ADD COLUMN IF NOT EXISTS face_id VARCHAR(64)"))
            await conn.execute(text("ALTER TABLE guests ADD COLUMN IF NOT EXISTS face_registered BOOLEAN DEFAULT FALSE"))
        except Exception:
            pass

        # 迁移：ai_security_logs 表新增 user_type
        try:
            await conn.execute(text("ALTER TABLE ai_security_logs ADD COLUMN IF NOT EXISTS user_type VARCHAR(20) DEFAULT 'guest'"))
        except Exception:
            pass

        # 迁移：guest_preferences 表
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

        # 迁移：chat_sessions 新增 summary 字段
        try:
            await conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS summary TEXT"))
        except Exception:
            pass

        await conn.run_sync(SQLModel.metadata.create_all)
