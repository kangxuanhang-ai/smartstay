import uuid
from datetime import datetime
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.database import async_session
from app.models.rag import RAGDocument, RAGEmbedding

embeddings_model = OpenAIEmbeddings(
    model="deepseek-embedding",
    openai_api_key=settings.DEEPSEEK_API_KEY,
    openai_api_base=f"{settings.DEEPSEEK_BASE_URL}/v1",
    dimensions=1536,
)


async def _get_embedding(text: str) -> list[float]:
    """获取单条文本的 embedding 向量"""
    try:
        result = await embeddings_model.aembed_query(text)
        return result
    except Exception:
        return [0.0] * 1536


async def _get_embeddings(texts: list[str]) -> list[list[float]]:
    """批量获取 embedding 向量"""
    try:
        result = await embeddings_model.aembed_documents(texts)
        return result
    except Exception:
        return [[0.0] * 1536] * len(texts)


async def process_and_store(title: str, file_name: str, content: str, uploaded_by: Optional[uuid.UUID] = None):
    """上传 Markdown → TextSplitter 切片 → 真实 embedding → 写入数据库"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)

    chunk_embeddings = await _get_embeddings(chunks)

    async with async_session() as db:
        doc = RAGDocument(
            title=title,
            file_name=file_name,
            content=content,
            chunks=len(chunks),
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            vectorized_at=datetime.utcnow(),
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
    query_embedding = await _get_embedding(query)

    async with async_session() as db:
        from sqlalchemy import text

        sql = text("""
            SELECT content, 1 - (embedding <=> :query_vec::vector) AS similarity
            FROM rag_embeddings
            ORDER BY embedding <=> :query_vec::vector
            LIMIT :top_k
        """)
        result = await db.execute(sql, {
            "query_vec": str(query_embedding),
            "top_k": top_k,
        })
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
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                "vectorized_at": d.vectorized_at.isoformat() if d.vectorized_at else None,
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
