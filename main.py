from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import  auth
# Import các router từ thư mục routers
from routers import transactions
from routers import fines
from routers import auth, fines, transactions, chat, cars, bookings # I
app = FastAPI(
    title="Hệ Thống Định Giá Xe",
    description="Backend API tích hợp AI định giá và Blockchain",
    version="1.0.0"
)

# Thiết lập CORS để cho phép Frontend kết nối tới Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Hoặc thay bằng ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# ĐĂNG KÝ CÁC MODULE (MỞ RỘNG DỄ DÀNG Ở ĐÂY)
# ==========================================
# Đưa toàn bộ API liên quan đến giao dịch vào prefix /api/v1/transactions
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"]) # Thêm các router khác vào đây khi bạn muốn mở rộng hệ thống. Ví dụ sau này bạn muốn làm thêm chức năng User, bạn chỉ cần tạo file routers/users.py và thêm:  
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(fines.router, prefix="/api/v1/fines", tags=["Fines"])
app.include_router(chat.router, prefix="/api", tags=["Chat AI"])
app.include_router(cars.router, prefix="/api/v1/cars", tags=["Cars"])
app.include_router(bookings.router, prefix="/api/v1/bookings", tags=["Bookings"])
# Ví dụ sau này bạn muốn làm thêm chức năng User, bạn chỉ cần tạo file routers/users.py và thêm:
# from routers import users
# app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

@app.get("/")
def root():
    return {"message": "Hệ thống Backend FastAPI đang chạy ổn định!"}