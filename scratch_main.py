from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from routers import auth, fines, transactions, chat, cars, bookings, payment
from services.relayer_worker import process_blockchain_queue

logger = logging.getLogger("main")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động worker nền
    worker_task = asyncio.create_task(process_blockchain_queue())
    logger.info("Relayer Worker started")
    yield
    # Dọn dẹp nếu cần
    worker_task.cancel()

app = FastAPI(
    title="Hệ Thống Định Giá Xe",
    description="Backend API tích hợp AI định giá và Blockchain",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(fines.router, prefix="/api/v1/fines", tags=["Fines"])
app.include_router(chat.router, prefix="/api", tags=["Chat AI"])
app.include_router(cars.router, prefix="/api/v1/cars", tags=["Cars"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])
app.include_router(payment.router) # Đã có prefix trong router

@app.get("/")
def root():
    return {"message": "Hệ thống Backend FastAPI đang chạy ổn định!"}
