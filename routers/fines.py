from pydantic import BaseModel
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

class FineCheckRequest(BaseModel):
    plate: str

@router.post("/check-real")
async def check_fines_mock_data(req: FineCheckRequest):
    # Làm sạch biển số
    clean_plate = req.plate.replace("-", "").replace(".", "").replace(" ", "").upper()
    
    # Lấy thời gian hiện tại để giả lập thời gian cập nhật
    current_time = datetime.now().strftime("%H:%M, %d/%m/%Y")

    # 1. KỊCH BẢN CÓ LỖI (Dùng để demo - Nhập biển có số 999)
    if "999" in clean_plate:
        return {
            "error": False,
            "status": "warning",
            "plate_number": clean_plate,
            "success": True,
            "total": 1,
            "type": "3",
            "updated_at": current_time,
            "vehicle_type": "car",
            "violations": [
                {
                    "bien_kiem_soat": clean_plate,
                    "mau_bien": "Nền trắng, chữ và số màu đen",
                    "loai_phuong_tien": "Ô tô",
                    "thoi_gian_vi_pham": "08:30, 20/08/2026",
                    "dia_diem_vi_pham": "Ngã tư Phạm Hùng - Khuất Duy Tiến, Hà Nội",
                    "hanh_vi_vi_pham": "Không chấp hành hiệu lệnh của đèn tín hiệu giao thông",
                    "trang_thai": "Chưa nộp phạt",
                    "don_vi_phat_hien": "Phòng CSGT Công an TP Hà Nội"
                }
            ]
        }

    # 2. KỊCH BẢN KHÔNG CÓ LỖI (Cấu trúc y hệt ảnh Preview bạn đã chụp)
    return {
        "error": False,
        "status": "warning",
        "plate_number": clean_plate,
        "success": True,
        "total": 1,
        "type": "3",
        "updated_at": current_time,
        "vehicle_type": "car",
        "violations": []
    }
    # ... [Phần code API /check-real phía trên giữ nguyên] ...

@router.post("/check-registry")
async def check_vehicle_registry(req: FineCheckRequest):
    clean_plate = req.plate.replace("-", "").replace(".", "").replace(" ", "").upper()
    
    # 1. KỊCH BẢN HẾT HẠN ĐĂNG KIỂM (Demo bằng cách nhập biển chứa số 999)
    if "999" in clean_plate:
        return {
            "success": True,
            "plate_number": clean_plate,
            "status": "expired",
            "message": "Phương tiện đã HẾT HẠN kiểm định!",
            "data": {
                "nhan_hieu": "TOYOTA",
                "so_khung": "RL412345678987",
                "so_may": "1NZ123456",
                "ngay_kiem_dinh": "10/01/2025",
                "han_kiem_dinh": "09/07/2025", # Đã hết hạn so với năm 2026
                "don_vi_kiem_dinh": "29-03V - Hà Nội"
            }
        }
        
    # 2. KỊCH BẢN CÒN HẠN ĐĂNG KIỂM (Bình thường)
    return {
        "success": True,
        "plate_number": clean_plate,
        "status": "valid",
        "message": "Phương tiện đang trong thời hạn kiểm định.",
        "data": {
            "nhan_hieu": "VINFAST",
            "so_khung": "VF598765432101",
            "so_may": "EVS987654",
            "ngay_kiem_dinh": "15/05/2026",
            "han_kiem_dinh": "14/11/2028", # Còn hạn dài
            "don_vi_kiem_dinh": "29-05V - Hà Nội"
        }
    }