from fastapi import APIRouter, HTTPException
from schemas import CarValuationRequest
from database import supabase
import joblib
import pandas as pd
import os
from utils.web3_validator import verify_transaction
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
    "vinfast": 0.35        # Điều chỉnh lại mốc khấu hao thực tế cho VinFast
}

# Hệ số tình trạng xe (1.0 là xe nguyên bản, không lỗi)
CONDITION_PENALTY_INDEX = {
    "perfect": 1.0,           # Xe nguyên bản
    "door_replaced": 0.95,    # Thay cửa, xước xát vỏ (Trừ 5%)
    "airbag_deployed": 0.85,  # Đã nổ túi khí (Trừ 15%)
    "major_accident": 0.80,   # Tai nạn nặng, đụng tới sát-xi (Trừ 20%)
    "flood_damage": 0.70      # Thủy kích, ngập nước (Trừ 30%)
}


MODEL_PATH = "ml_models/car_pricing_model.pkl"
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
    
    if not model:
        raise HTTPException(status_code=500, detail="Mô hình AI chưa khởi tạo.")

    # Loại bỏ txhash khỏi data để đưa vào model học máy
    car_data = data.model_dump(exclude={"txhash"}) 
    df_input = pd.DataFrame([car_data])
    
    try:
        # 2.1. AI dự đoán giá gốc
        predicted_price_pln = model.predict(df_input)[0]
        base_price_vnd = predicted_price_pln * PLN_TO_VND_RATE
        
        # 2.2. Hệ số thương hiệu
        brand_key = data.Vehicle_brand.lower()
        reputation_score = BRAND_REPUTATION_INDEX.get(brand_key, 0.7)
        
        # 2.3. HỆ SỐ TÌNH TRẠNG XE CHI TIẾT
        condition_score = 1.0 
        
        # A. Xử lý các lỗi nghiêm trọng trong mảng (Ngập nước, bổ máy...)
        for condition in data.vehicle_conditions:
            condition_score *= CONDITION_PENALTY_INDEX.get(condition.lower(), 1.0)
            
        # B. Xử lý số cửa đã thay (Ví dụ: mỗi cánh cửa thay bị trừ 2% giá trị)
        if data.doors_replaced > 0:
            condition_score *= (1.0 - (data.doors_replaced * 0.02))

        # C. Xử lý tình trạng sơn xi/xước xát
        if data.scratch_severity == "minor":
            condition_score *= 0.98 # Trừ 2% chi phí dọn sơn dặm
        elif data.scratch_severity == "major":
            condition_score *= 0.93 # Trừ 7% chi phí gò hàn, làm đồng nặng
            
        # D. Xử lý số đời chủ (Mỗi đời chủ tiếp theo bị trừ 3% giá trị)
        if data.previous_owners > 1:
            penalty_for_owners = (data.previous_owners - 1) * 0.03
            condition_score *= (1.0 - penalty_for_owners)
            
        # E. Xử lý đặc thù Xe Điện (Khấu hao nhanh & Phân loại pin)
        if data.Fuel_type.lower() in ["electric", "ev"]:
            if data.ev_battery_type == "rented":
                # Thuê pin: Giá xe rất rẻ vì không bao gồm tài sản pin (Trừ 30%)
                condition_score *= 0.70 
            elif data.ev_battery_type == "bought":
                # Mua đứt pin: Xe điện mất giá nhanh do rủi ro chai pin so với xe xăng (Trừ 15%)
                condition_score *= 0.85 
                
        # 2.4. ĐỊNH GIÁ BIỂN SỐ
        if data.license_plate:
            # Lấy 2 ký tự đầu tiên của biển số (VD: "30A-123.45" -> "30")
            plate_prefix = str(data.license_plate)[:2] 
            
            if plate_prefix in CITY_PLATE_PREFIXES:
                # Nếu là biển Hà Nội hoặc TP.HCM -> Tăng 1% giá trị xe
                condition_score *= 1.01 
                print(f"Xe biển thành phố ({plate_prefix}), phải trả thêm 1% giá trị.")
                
            if "-" in data.license_plate:
                # Cắt lấy phần đuôi số và bỏ dấu chấm (VD: "30G-888.88" -> "88888")
                tail_numbers = data.license_plate.split("-")[1].replace(".", "").strip()
                
                # A. KIỂM TRA NGŨ QUÝ (5 số y hệt nhau, VD: 88888, 99999)
                if len(tail_numbers) == 5 and len(set(tail_numbers)) == 1:
                    condition_score *= 1.10 # Cộng 10%
                    print(f"VIP! Biển Ngũ Quý ({tail_numbers}), cộng 10%")
                
                # B. KIỂM TRA BIỂN ĐẸP (Nếu không phải ngũ quý thì xét tiếp các giải phụ)
                else:
                    is_beautiful = False
                    
                    # - Tứ quý (4 số đuôi giống nhau, VD: 19999, hoặc biển 4 số cũ 8888)
                    if len(tail_numbers) >= 4 and len(set(tail_numbers[-4:])) == 1:
                        is_beautiful = True
                    # - Sảnh tiến (VD: 12345, 56789, 34567...)
                    elif tail_numbers in ["12345", "23456", "34567", "45678", "56789", "6789"]:
                        is_beautiful = True
                    # - Lộc phát, Thần tài (Đuôi kết thúc bằng 68, 86, 39, 79)
                    elif len(tail_numbers) >= 2 and tail_numbers[-2:] in ["68", "86", "39", "79"]:
                        is_beautiful = True
                        
                    if is_beautiful:
                        condition_score *= 1.03 # Cộng 3%
                        print(f"Biển đẹp ({tail_numbers}), cộng 3%")
                        
        # 2.5. Chốt giá cuối cùng
        final_predicted_price_vnd = round(base_price_vnd * reputation_score * condition_score)
        
        # Format hiển thị
        formatted_price_vnd = f"{final_predicted_price_vnd:,}".replace(',', '.') + " VNĐ"
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi dự đoán: {str(e)}")

    # ==========================================
    # PHẦN 3: LƯU TRỮ DATABASE VÀ TRẢ KẾT QUẢ
    # ==========================================

    # 3.1. Đóng gói dữ liệu chuẩn bị gửi lên Supabase
    transaction_record = {
        "txhash": data.txhash,
        "predicted_price": final_predicted_price_vnd,  
        "brand": data.Vehicle_brand,
        "model": data.Vehicle_model,
        "year": int(data.Production_year),
        "mileage": int(data.Mileage_km), 
        "fuel_type": data.Fuel_type,
        "license_plate": data.license_plate,
        "full_data": data.model_dump() # JSONB lưu toàn bộ thông tin
    }

    print("--- DỮ LIỆU CHUẨN BỊ GỬI LÊN SUPABASE ---")
    print(transaction_record)

    # 3.2. Ghi nhận giao dịch
    try:
        db_response = supabase.table("transactions").insert(transaction_record).execute()
        
        print("--- PHẢN HỒI TỪ SUPABASE ---")
        print(db_response)
        
    except Exception as e:
        print("--- LỖI SUPABASE TRẢ VỀ ---")
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Lỗi lưu DB: {str(e)}")

    # 3.3. Trả kết quả về cho Frontend
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
        
        # Trả về toàn bộ dữ liệu cho Frontend
        return {
            "status": "success",
            "message": "Lấy thông tin xe thành công",
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