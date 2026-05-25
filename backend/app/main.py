from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.core.seed import seed_default_users, seed_default_rooms
from app.api import auth, rooms, orders, work_orders, admin, consumptions
from app.api.ai import router as ai_router
from app.api.rag import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_default_users()
    await seed_default_rooms()
    yield


app = FastAPI(title="SmartStay API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(orders.router)
app.include_router(work_orders.router)
app.include_router(admin.router)
app.include_router(consumptions.router)
app.include_router(ai_router)
app.include_router(rag_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}
