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

# 懒加载 embedder，避免 uvicorn --reload 子进程导致问题
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


# ── Query 改写 ──
_llm_rewriter = None


def _get_rewriter():
    global _llm_rewriter
    if _llm_rewriter is None:
        from langchain_deepseek import ChatDeepSeek
        from app.core.config import settings
        _llm_rewriter = ChatDeepSeek(
            model="deepseek-chat",
            api_key=settings.DEEPSEEK_API_KEY,
            temperature=0,
        )
    return _llm_rewriter


async def rewrite_query(user_input: str) -> list[str]:
    """LLM 将用户输入改写为 2-3 个搜索关键词，失败时 fallback 到原始输入"""
    try:
        rewriter = _get_rewriter()
        prompt = (
            "将以下住客问题改写为 2-3 个适合酒店知识库搜索的关键词，每行一个。"
            "只输出关键词，不要解释。\n\n"
            f"问题：{user_input}"
        )
        resp = await rewriter.ainvoke(prompt)
        keywords = [line.strip() for line in resp.content.strip().split("\n") if line.strip()]
        return keywords if keywords else [user_input]
    except Exception as e:
        logger.warning(f"rewrite_query failed, using original: {e}")
        return [user_input]


async def process_and_store(title: str, file_name: str, content: str, uploaded_by: Optional[uuid.UUID] = None):
    """上传 Markdown → TextSplitter 切片 → 本地 embedding → 写入数据库"""
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=80)
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


async def reindex_all():
    """用新的 chunk_size/overlap 重新处理所有文档的 embedding"""
    from sqlmodel import delete as sqlmodel_delete

    async with async_session() as db:
        result = await db.execute(select(RAGDocument))
        docs = result.scalars().all()

        # 清除旧 embeddings
        await db.execute(sqlmodel_delete(RAGEmbedding))
        await db.commit()

        splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=80)
        total_chunks = 0

        for doc in docs:
            chunks = splitter.split_text(doc.content)
            chunk_embeddings = _embed_texts(chunks)

            for i, chunk in enumerate(chunks):
                emb = RAGEmbedding(
                    document_id=doc.id,
                    chunk_index=i,
                    content=chunk,
                    embedding=chunk_embeddings[i],
                )
                db.add(emb)

            doc.chunks = len(chunks)
            doc.vectorized_at = cst_now()
            total_chunks += len(chunks)

        await db.commit()

    return {"documents": len(docs), "total_chunks": total_chunks}


async def query_vector_store(query: str, top_k: int = 5) -> list[str]:
    """pgvector 余弦相似度检索知识库（支持 query 改写 + 多关键词混合检索）"""
    from sqlalchemy import cast, func, or_
    from pgvector.sqlalchemy import Vector

    # Query 改写：将用户输入扩展为多个搜索关键词
    keywords = await rewrite_query(query)

    async with async_session() as db:
        from sqlalchemy import select as sa_select

        all_results = {}  # content -> similarity，去重

        for kw in keywords:
            query_vec = _embed_query(kw)
            vec_literal = cast(query_vec, Vector(EMBEDDING_DIM))
            distance = RAGEmbedding.embedding.cosine_distance(vec_literal)
            similarity = 1 - distance

            stmt = (
                sa_select(RAGEmbedding.content, similarity.label("similarity"))
                .where(similarity > 0.3)
                .order_by(distance)
                .limit(top_k)
            )
            result = await db.execute(stmt)
            rows = result.fetchall()
            for row in rows:
                content, sim = row[0], row[1]
                if content not in all_results or sim > all_results[content]:
                    all_results[content] = sim

        # 按相似度排序，取 top_k
        sorted_results = sorted(all_results.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = [content for content, _ in sorted_results]

        # 关键词兜底：如果向量搜索没结果，用 LIKE 搜索
        if not results:
            for kw in keywords[:2]:  # 只用前两个关键词
                keyword = f"%{kw[:4]}%"
                kw_stmt = (
                    sa_select(RAGEmbedding.content)
                    .where(RAGEmbedding.content.like(keyword))
                    .limit(top_k)
                )
                kw_result = await db.execute(kw_stmt)
                for row in kw_result.fetchall():
                    if row[0] not in results:
                        results.append(row[0])

        return results[:top_k]


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