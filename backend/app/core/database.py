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

        await conn.run_sync(SQLModel.metadata.create_all)
