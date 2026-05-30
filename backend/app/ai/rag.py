import uuid
import logging
from datetime import datetime
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.database import async_session
from app.core.utils import cst_now, cst_isoformat
from app.models.rag import RAGDocument, RAGEmbedding

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 512  # bge-small-zh-v1.5 输出维度

# 懒加载 embedder，避免 uvicorn --reload 子进程导入问题
_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    return _embedder


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """同步批量 embedding"""
    return [vec.tolist() for vec in _get_embedder().embed(texts)]


def _embed_query(text: str) -> list[float]:
    """同步单条 embedding"""
    return list(next(iter(_get_embedder().embed([text]))))


async def process_and_store(title: str, file_name: str, content: str, uploaded_by: Optional[uuid.UUID] = None):
    """上传 Markdown → TextSplitter 切片 → 本地 embedding → 写入数据库"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)

    chunk_embeddings = _embed_texts(chunks)

    async with async_session() as db:
        doc = RAGDocument(
            title=title,
            file_name=file_name,
            content=content,
            chunks=len(chunks),
            uploaded_by=uploaded_by,
            uploaded_at=cst_now(),
            vectorized_at=cst_now(),
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        for i, chunk in enumerate(chunks):
            emb = RAGEmbedding(
                document_id=doc.id,
                chunk_index=i,
                content=chunk,
                embedding=chunk_embeddings[i],
            )
            db.add(emb)

        await db.commit()

    return {"document_id": str(doc.id), "chunks": len(chunks)}


async def query_vector_store(query: str, top_k: int = 5) -> list[str]:
    """pgvector 余弦相似度检索知识库"""
    from sqlalchemy import cast, func
    from pgvector.sqlalchemy import Vector

    query_vec = _embed_query(query)

    async with async_session() as db:
        from sqlalchemy import select as sa_select

        vec_literal = cast(query_vec, Vector(EMBEDDING_DIM))
        distance = RAGEmbedding.embedding.cosine_distance(vec_literal)
        stmt = (
            sa_select(RAGEmbedding.content, (1 - distance).label("similarity"))
            .order_by(distance)
            .limit(top_k)
        )
        result = await db.execute(stmt)
        rows = result.fetchall()
        return [row[0] for row in rows if row[1] > 0.1]


async def get_all_documents():
    """获取所有知识库文档列表"""
    async with async_session() as db:
        from sqlmodel import select
        result = await db.execute(select(RAGDocument).order_by(RAGDocument.uploaded_at.desc()))
        docs = result.scalars().all()
        return [
            {
                "id": str(d.id),
                "title": d.title,
                "file_name": d.file_name,
                "chunks": d.chunks,
                "uploaded_at": cst_isoformat(d.uploaded_at),
                "vectorized_at": cst_isoformat(d.vectorized_at),
            }
            for d in docs
        ]


async def delete_document(doc_id: str):
    """级联删除文档及其 embeddings"""
    async with async_session() as db:
        from sqlmodel import delete
        await db.execute(delete(RAGEmbedding).where(RAGEmbedding.document_id == uuid.UUID(doc_id)))
        await db.execute(delete(RAGDocument).where(RAGDocument.id == uuid.UUID(doc_id)))
        await db.commit()
    return {"deleted": doc_id}
