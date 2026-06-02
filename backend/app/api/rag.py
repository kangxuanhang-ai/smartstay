import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import Staff
from app.ai.rag import process_and_store, get_all_documents, delete_document

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    title: str = Form(""),
    current_user: Staff = Depends(require_role("manager")),
):
    """B端店长上传 Markdown 知识库文档"""
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="仅支持 .md 格式的 Markdown 文件")

    content_bytes = await file.read()
    if len(content_bytes) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="文件过大，最大支持5MB")
    content = content_bytes.decode("utf-8")
    if not content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    result = await process_and_store(
        title=title or file.filename,
        file_name=file.filename,
        content=content,
        uploaded_by=current_user.id,
    )
    return {"message": f"上传成功，已切片为 {result['chunks']} 个片段", "document_id": result["document_id"]}


@router.get("/documents")
async def list_documents(
    current_user: Staff = Depends(require_role("manager")),
):
    """获取所有知识库文档列表"""
    return await get_all_documents()


@router.delete("/documents/{doc_id}")
async def remove_document(
    doc_id: str,
    current_user: Staff = Depends(require_role("manager")),
):
    """删除知识库文档及其所有关联 embeddings"""
    return await delete_document(doc_id)
