from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import init_db
from app.core.seed import seed_default_users, seed_default_rooms
from app.api import auth, rooms, orders, work_orders


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_default_users()
    await seed_default_rooms()
    yield


app = FastAPI(title="SmartStay API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(orders.router)
app.include_router(work_orders.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}
