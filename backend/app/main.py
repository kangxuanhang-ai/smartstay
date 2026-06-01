from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import init_db
from app.core.seed import seed_default_users, seed_default_rooms, seed_hotel_info, seed_facilities
from app.api import auth, rooms, orders, work_orders, admin, consumptions
from app.api import hotel
from app.api.ai import router as ai_router
from app.api.face import router as face_router
from app.api.rag import router as rag_router
from app.ws.manager import manager

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_default_users()
    await seed_default_rooms()
    await seed_hotel_info()
    await seed_facilities()

    from app.tasks.audit import generate_audit_report
    scheduler.add_job(generate_audit_report, 'cron', hour=4, minute=0, id='daily_audit', replace_existing=True)
    from app.core.utils import cst_now
    scheduler.add_job(generate_audit_report, 'date', run_date=cst_now() + timedelta(seconds=30), id='initial_audit')
    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(title="SmartStay API", version="0.3.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "detail": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(orders.router)
app.include_router(work_orders.router)
app.include_router(admin.router)
app.include_router(consumptions.router)
app.include_router(hotel.router)
app.include_router(ai_router)
app.include_router(rag_router)
app.include_router(face_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    result = await manager.connect(websocket, token)
    if not result:
        return
    user_id, role = result
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}
