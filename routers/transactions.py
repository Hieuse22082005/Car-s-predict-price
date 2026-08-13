from fastapi import APIRouter, HTTPException
from schemas import CarValuationRequest
from database import supabase
import joblib
import pandas as pd
import os
from utils.web3_validator import verify_transaction
import hashlib
import uuid
import json
# Import hàm kiểm tra ở Bước 2
router = APIRouter()
CITY_PLATE_PREFIXES = [
    # Hà Nội
    "29", "30", "31", "32", "33", "40",
    # TP. Hồ Chí Minh
    "41", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59"
]

BRAND_REPUTATION_INDEX = {
    "toyota": 1.0,         # Hãng giữ giá nhất thị trường
    "honda": 0.95,
    "mazda": 0.85,
    "kia": 0.85,
    "hyundai": 0.85,
    "mitsubishi": 0.85,
    "ford": 0.80,
    "mercedes-benz": 0.55, # Xe sang Đức rớt giá nhanh ở VN
    "bmw": 0.50,
    "audi": 0.50,
    "vinfast": 0.9       # Điều chỉnh lại mốc khấu hao thực tế cho VinFast
}

# Hệ số tình trạng xe (1.0 là xe nguyên bản, không lỗi)
CONDITION_PENALTY_INDEX = {
    "perfect": 1.0,           # Xe nguyên bản
    "door_replaced": 0.95,    # Thay cửa, xước xát vỏ (Trừ 5%)
    "airbag_deployed": 0.85,  # Đã nổ túi khí (Trừ 15%)
    "major_accident": 0.80,   # Tai nạn nặng, đụng tới sát-xi (Trừ 20%)
    "flood_damage": 0.70      # Thủy kích, ngập nước (Trừ 30%)
}

# ĐÃ SỬA: Dùng đường dẫn tuyệt đối để Render tải được file AI không bị lỗi 500
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "car_pricing_model.pkl")

if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

# Khai báo tỷ giá chuyển đổi (PLN -> VNĐ)
PLN_TO_VND_RATE = 7040.57

from fastapi import APIRouter, HTTPException
# Đảm bảo bạn đã import verify_payment từ file web3_validator.py của bạn
# from web3_validator import verify_payment 
# from database import supabase (tùy thuộc vào cách bạn cấu hình supabase)

@router.post("/evaluate")
async def evaluate_and_save_transaction(data: CarValuationRequest):
    # ==========================================
    # PHẦN 1: BẢO MẬT & XÁC THỰC THANH TOÁN
    # ==========================================
    
    # 1.1. CHỐT CHẶN 1: KIỂM TRA THANH TOÁN TRÊN BLOCKCHAIN
    is_paid = verify_transaction(data.txhash)
    if not is_paid:
        raise HTTPException(
            status_code=400, 
            detail="Giao dịch không hợp lệ, chưa thành công hoặc không đủ 0.001 phí!"
        )

    # 1.2. CHỐT CHẶN 2: CHỐNG REPLAY ATTACK (DÙNG LẠI TXHASH CŨ)
    try:
        # Truy vấn Supabase xem txhash này đã tồn tại chưa
        db_check = supabase.table("transactions").select("txhash").eq("txhash", data.txhash).execute()
        
        # Nếu danh sách trả về có dữ liệu nghĩa là txhash đã bị trùng
        if len(db_check.data) > 0:
            raise HTTPException(
                status_code=400, 
                detail="Mã giao dịch này đã được sử dụng để định giá rồi!"
            )
    except Exception as e:
        # Xử lý riêng lỗi nếu bắt nguồn từ HTTPException ở trên để không bị đè lỗi
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Lỗi kiểm tra lịch sử giao dịch: {str(e)}")

    # ==========================================
    # PHẦN 2: LOGIC AI VÀ ĐỊNH GIÁ XE
    # ==========================================
    
    # ==========================================
    # PHẦN 2: LOGIC AI VÀ ĐỊNH GIÁ XE (ĐÃ FIX)
    # ==========================================
    
    if not model:
        raise HTTPException(status_code=500, detail="Mô hình AI chưa khởi tạo.")

    # 2.0 BẢNG GIÁ SÀN THỰC TẾ TẠI VIỆT NAM (Giá xe mới ~ Lăn bánh)
    VIETNAM_CAR_MARKET_PRICE = {
        "vinfast_vf 5": 468000000,
        "vinfast_vf 8": 1090000000,
        "vinfast_vf 9": 1490000000,
        "vinfast_fadil": 350000000,
        "vinfast_lux a2.0": 850000000,
        "toyota_vios": 550000000,
        "toyota_camry": 1100000000,
        "honda_city": 550000000,
        "honda_cr-v": 1050000000,
        "mazda_cx-5": 850000000,
        "mazda_mazda 3": 700000000,
        "ford_ranger": 850000000,
        "ford_everest": 1200000000
    }

    car_data = data.model_dump(exclude={"txhash"}) 
    df_input = pd.DataFrame([car_data])
    
    try:
        # 2.1. TÌM GIÁ GỐC (Ưu tiên Database nội địa trước, nếu không có mới dùng AI Châu Âu)
        car_key = f"{data.Vehicle_brand.lower()}_{data.Vehicle_model.lower()}"
        
        if car_key in VIETNAM_CAR_MARKET_PRICE:
            # Nếu xe có trong dữ liệu Việt Nam -> Lấy giá niêm yết
            base_price_vnd = VIETNAM_CAR_MARKET_PRICE[car_key]
        else:
            # Nếu xe lạ, dùng model AI predict
            predicted_price_pln = model.predict(df_input)[0]
            base_price_vnd = predicted_price_pln * PLN_TO_VND_RATE
        
        # Trừ khấu hao theo số năm sử dụng (Mỗi năm giảm 8%)
        current_year = 2026 # Bạn đang set năm giả định là 2026
        car_age = current_year - data.Production_year
        if car_age > 0:
            base_price_vnd *= (1 - (car_age * 0.08)) 
            
        # Trừ khấu hao theo số km (Cứ 10.000km trừ 1% giá trị)
        if data.Mileage_km > 0:
            base_price_vnd *= (1 - (data.Mileage_km / 10000 * 0.01))

        # 2.2. Hệ số thương hiệu
        brand_key = data.Vehicle_brand.lower()
        reputation_score = BRAND_REPUTATION_INDEX.get(brand_key, 0.7)
        
        # 2.3. HỆ SỐ TÌNH TRẠNG XE CHI TIẾT
        condition_score = 1.0 
        
        # A. Xử lý lỗi nghiêm trọng
        for condition in data.vehicle_conditions:
            condition_score *= CONDITION_PENALTY_INDEX.get(condition.lower(), 1.0)
            
        # B. Số cửa đã thay (Mỗi cửa trừ 2%)
        if data.doors_replaced > 0:
            condition_score *= (1.0 - (data.doors_replaced * 0.02))

        # C. Sơn xi/xước xát
        if data.scratch_severity == "minor":
            condition_score -= 0.02 # Trừ thẳng 2% cho chuẩn
        elif data.scratch_severity == "major":
            condition_score -= 0.07 # Trừ thẳng 7%
            
        # D. Số đời chủ (Từ chủ thứ 2 trở đi, mỗi đời trừ 3%)
        if data.previous_owners > 1:
            condition_score -= ((data.previous_owners - 1) * 0.03)
            
        # E. Xử lý đặc thù Xe Điện (Chỉ trừ thêm khi xe đã sử dụng cũ, xe mới không trừ)
        if data.Fuel_type.lower() in ["electric", "ev"] and car_age > 2:
            if data.ev_battery_type == "rented":
                condition_score -= 0.15 # Giảm mức phạt xuống 15%
            elif data.ev_battery_type == "bought":
                condition_score -= 0.10 # Giảm mức phạt xuống 10%
                
        # Ngăn không cho condition_score rớt xuống số âm
        condition_score = max(condition_score, 0.3)

        # 2.4. ĐỊNH GIÁ BIỂN SỐ (Tính bằng tiền Tỷ thay vì %)
        plate_bonus_vnd = 0
        if data.license_plate:
            plate_prefix = str(data.license_plate)[:2] 
            
            if plate_prefix in CITY_PLATE_PREFIXES:
                # Biển phố + 20 triệu
                plate_bonus_vnd += 20000000 
                
            if "-" in data.license_plate:
                tail_numbers = data.license_plate.split("-")[1].replace(".", "").strip()
                
                # A. Ngũ Quý -> CỘNG TRỰC TIẾP 1 TỶ VNĐ
                if len(tail_numbers) == 5 and len(set(tail_numbers)) == 1:
                    plate_bonus_vnd += 500000000 
                    print(f"VIP! Biển Ngũ Quý ({tail_numbers}), cộng 1 Tỷ VNĐ")
                
                # B. Tứ Quý -> CỘNG 300 TRIỆU VNĐ
                elif len(tail_numbers) >= 4 and len(set(tail_numbers[-4:])) == 1:
                    plate_bonus_vnd += 300000000
                
                # C. Sảnh tiến -> CỘNG 200 TRIỆU VNĐ
                elif tail_numbers in ["12345", "23456", "34567", "45678", "56789", "6789"]:
                    plate_bonus_vnd += 200000000
                    
                # D. Thần tài, lộc phát -> CỘNG 50 TRIỆU VNĐ
                elif len(tail_numbers) >= 2 and tail_numbers[-2:] in ["68", "86", "39", "79"]:
                    plate_bonus_vnd += 50000000
                        
        # 2.5. CHỐT GIÁ CUỐI CÙNG = (Giá gốc * Độ uy tín * Tình trạng) + Tiền biển số
        final_predicted_price_vnd = round(base_price_vnd * reputation_score * condition_score) + plate_bonus_vnd
        
        # Format hiển thị (Ví dụ: 1.500.000.000 VNĐ)
        formatted_price_vnd = f"{int(final_predicted_price_vnd):,}".replace(',', '.') + " VNĐ"
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi dự đoán: {str(e)}")

    # ==========================================
    # PHẦN 3: LƯU TRỮ DATABASE VÀ TRẢ KẾT QUẢ
    # ==========================================

    # 3.1. TẠO CHỮ KÝ SỐ BẢO MẬT (CHỐNG SỬA ĐỔI DATABASE)
    random_salt = uuid.uuid4().hex
    data_to_protect = {
        "txhash": data.txhash,
        "predicted_price": final_predicted_price_vnd,
        "license_plate": data.license_plate
    }
    data_string = json.dumps(data_to_protect, sort_keys=True) + random_salt
    data_signature = hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    # 3.2. Đóng gói dữ liệu chuẩn bị gửi lên Supabase
    transaction_record = {
        "txhash": data.txhash,
        "predicted_price": final_predicted_price_vnd,  
        "brand": data.Vehicle_brand,
        "model": data.Vehicle_model,
        "year": int(data.Production_year),
        "mileage": int(data.Mileage_km), 
        "fuel_type": data.Fuel_type,
        "license_plate": data.license_plate,
        "full_data": data.model_dump(), # JSONB lưu toàn bộ thông tin
        "user_email": getattr(data, 'user_email', None) or car_data.get('user_email'),
        "salt": random_salt,              # CỘT MỚI: Sinh ra chuỗi ngẫu nhiên
        "data_signature": data_signature  # CỘT MỚI: Chữ ký số
    }

    print("--- DỮ LIỆU CHUẨN BỊ GỬI LÊN SUPABASE ---")
    print(transaction_record)

    # 3.3. Ghi nhận giao dịch
    try:
        db_response = supabase.table("transactions").insert(transaction_record).execute()
        
        print("--- PHẢN HỒI TỪ SUPABASE ---")
        print(db_response)
        
    except Exception as e:
        print("--- LỖI SUPABASE TRẢ VỀ ---")
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Lỗi lưu DB: {str(e)}")

    # 3.4. Trả kết quả về cho Frontend
    return {
        "status": "success",
        "message": "Đã định giá và ghi nhận giao dịch vào DB",
        "data": {
            "predicted_price_raw": final_predicted_price_vnd, 
            "predicted_price_display": formatted_price_vnd, 
            "license_plate": data.license_plate,
            "txhash": data.txhash
        }
    }

@router.get("/{txhash}")
async def get_transaction_details(txhash: str):
    """
    API lấy toàn bộ thông tin chi tiết của một giao dịch định giá dựa vào txhash.
    """
    try:
        # Truy vấn vào bảng transactions, tìm dòng có cột txhash khớp với txhash FE gửi lên
        db_response = supabase.table("transactions").select("*").eq("txhash", txhash).execute()
        
        # Nếu mảng data trả về rỗng -> Không tìm thấy
        if not db_response.data or len(db_response.data) == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"Không tìm thấy dữ liệu xe với mã txhash: {txhash}"
            )
            
        # Lấy bản ghi đầu tiên tìm được
        record = db_response.data[0]
        
        # ==========================================
        # KIỂM TRA TÍNH TOÀN VẸN CỦA DỮ LIỆU
        # ==========================================
        stored_salt = record.get("salt")
        stored_signature = record.get("data_signature")
        is_tampered = False
        
        if stored_salt and stored_signature:
            current_data = {
                "txhash": record.get("txhash"),
                "predicted_price": record.get("predicted_price"),
                "license_plate": record.get("license_plate")
            }
            # Băm lại dữ liệu lấy từ DB
            current_string = json.dumps(current_data, sort_keys=True) + stored_salt
            current_signature = hashlib.sha256(current_string.encode('utf-8')).hexdigest()
            
            # So sánh mã băm hiện tại với chữ ký lúc mới tạo
            if current_signature != stored_signature:
                is_tampered = True
        
        # Trả về toàn bộ dữ liệu cho Frontend
        return {
            "status": "success",
            "message": "Lấy thông tin xe thành công",
            "is_tampered": is_tampered, # Gửi cờ báo động về Frontend
            "data": {
                "id": record.get("id"),
                "created_at": record.get("created_at"),
                "txhash": record.get("txhash"),
                "license_plate": record.get("license_plate"),
                "predicted_price_vnd": record.get("predicted_price"),
                
                # Đây chính là "kho báu" chứa 100% dữ liệu FE đã gửi lên ban đầu
                "original_car_info": record.get("full_data") 
            }
        }
        
    except Exception as e:
        # Nếu lỗi là do không tìm thấy (404) thì ném thẳng ra
        if isinstance(e, HTTPException):
            raise e
        # Bắt các lỗi kết nối DB khác
        raise HTTPException(status_code=500, detail=f"Lỗi truy xuất dữ liệu: {str(e)}")