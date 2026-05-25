import uuid
from datetime import datetime
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.database import async_session
from app.models.rag import RAGDocument, RAGEmbedding


async def process_and_store(title: str, file_name: str, content: str, uploaded_by: Optional[uuid.UUID] = None):
    """上传 Markdown → TextSplitter 切片(chunk=500, overlap=50) → 写入数据库"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)

    async with async_session() as db:
        doc = RAGDocument(
            title=title,
            file_name=file_name,
            content=content,
            chunks=len(chunks),
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            vectorized_at=datetime.utcnow(),  # 本地切片无需远程向量化
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        for i, chunk in enumerate(chunks):
            emb = RAGEmbedding(
                document_id=doc.id,
                chunk_index=i,
                content=chunk,
                embedding=[0.0] * 1536,  # 占位向量（后续可替换为真实 embedding）
            )
            db.add(emb)

        await db.commit()

    return {"document_id": str(doc.id), "chunks": len(chunks)}


async def query_vector_store(query: str, top_k: int = 5) -> list[str]:
    """关键词匹配 + 相似度排序检索知识库"""
    async with async_session() as db:
        from sqlmodel import select
        result = await db.execute(select(RAGEmbedding))
        rows = result.scalars().all()

        if not rows:
            return []

        # 基于关键词匹配度排序
        query_lower = query.lower()
        scored = []
        for row in rows:
            content_lower = row.content.lower()
            score = sum(1 for word in query_lower.split() if word in content_lower)
            if score > 0:
                scored.append((score, row.content))

        scored.sort(key=lambda x: -x[0])
        return [content for _, content in scored[:top_k]]


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
