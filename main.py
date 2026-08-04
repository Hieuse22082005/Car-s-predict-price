from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import các router từ thư mục routers
from routers import transactions

app = FastAPI(
    title="Hệ Thống Định Giá Xe",
    description="Backend API tích hợp AI định giá và Blockchain",
    version="1.0.0"
)

# Thiết lập CORS để cho phép Frontend kết nối tới Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Trong môi trường production, hãy thay bằng domain thực tế của Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# ĐĂNG KÝ CÁC MODULE (MỞ RỘNG DỄ DÀNG Ở ĐÂY)
# ==========================================
# Đưa toàn bộ API liên quan đến giao dịch vào prefix /api/v1/transactions
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["Transactions"]) # Thêm các router khác vào đây khi bạn muốn mở rộng hệ thống. Ví dụ sau này bạn muốn làm thêm chức năng User, bạn chỉ cần tạo file routers/users.py và thêm:  

# Ví dụ sau này bạn muốn làm thêm chức năng User, bạn chỉ cần tạo file routers/users.py và thêm:
# from routers import users
# app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

@app.get("/")
def root():
    return {"message": "Hệ thống Backend FastAPI đang chạy ổn định!"}