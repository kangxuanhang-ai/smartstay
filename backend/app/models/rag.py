import uuid
from datetime import datetime
from typing import Any, Optional
from sqlmodel import Field, SQLModel, Column
from pgvector.sqlalchemy import Vector

from app.core.utils import cst_now


class RAGDocument(SQLModel, table=True):
    __tablename__ = "rag_documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=200)
    file_name: str = Field(max_length=200)
    content: str
    chunks: int = Field(default=0)
    uploaded_by: Optional[uuid.UUID] = Field(default=None, foreign_key="staff.id")
    uploaded_at: datetime = Field(default_factory=cst_now)
    vectorized_at: Optional[datetime] = Field(default=None)


class RAGEmbedding(SQLModel, table=True):
    __tablename__ = "rag_embeddings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="rag_documents.id")
    chunk_index: int
    content: str
    embedding: Any = Field(default=None, sa_column=Column(Vector(512)))
