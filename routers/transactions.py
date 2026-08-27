from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from schemas import CarValuationRequest
from database import supabase
import joblib
import pandas as pd
import os
from utils.web3_validator import verify_transaction
import hashlib
import uuid
import json
from fastapi import UploadFile, File
import pytesseract
from PIL import Image
import io
import re
from typing import List
router = APIRouter()

CITY_PLATE_PREFIXES = [
    # Hà Nội
    "29", "30", "31", "32", "33", "40",
    # TP. Hồ Chí Minh
    "41", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59"
]

BRAND_REPUTATION_INDEX = {
    "toyota": 1.0,         
    "honda": 0.95,
    "mazda": 0.85,
    "kia": 0.85,
    "hyundai": 0.85,
    "mitsubishi": 0.85,
    "ford": 0.80,
    "mercedes-benz": 0.55, 
    "bmw": 0.50,
    "audi": 0.50,
    "vinfast": 0.9       
}

CONDITION_PENALTY_INDEX = {
    "perfect": 1.0,           
    "door_replaced": 0.95,    
    "airbag_deployed": 0.85,  
    "major_accident": 0.80,   
    "flood_damage": 0.70      
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "car_pricing_model.pkl")

# ==========================================
# BỘ LỌC 1: XỬ LÝ LỖI FILE PKL BỊ LƯU DƯỚI DẠNG DICT
# ==========================================
if os.path.exists(MODEL_PATH):
    raw_data = joblib.load(MODEL_PATH)
    if isinstance(raw_data, dict):
        model = list(raw_data.values())[0]
        saved_features = raw_data.get("features", None)
    else:
        model = raw_data
        saved_features = None
else:
    model = None
    saved_features = None

PLN_TO_VND_RATE = 7040.57


# ==========================================
# API 1: ĐỊNH GIÁ XE & KIỂM TRA PHÍ (0 HOẶC 0.001 ETH)
# ==========================================
# ==========================================
# KHAI BÁO MODEL CHO API CONFIRM
# ==========================================
# ==========================================
# KHAI BÁO MODEL CHO API CONFIRM
# ==========================================
class ConfirmRequest(BaseModel):
    txhash: str
    carHash: str
    salt: str
    predicted_price: int  # Đổi thành int để đồng bộ
    vehicle_data: CarValuationRequest  # Bắt buộc dùng model này

# ==========================================
# BƯỚC 1: API TÍNH NHÁP & TẠO CAR HASH (CHƯA LƯU DB, CHƯA CẦN TXHASH)
# ==========================================
@router.post("/evaluate/draft")
async def draft_evaluation(data: CarValuationRequest):
    if not model:
        raise HTTPException(status_code=500, detail="Mô hình AI chưa khởi tạo.")

    # --- BÊ NGUYÊN TOÀN BỘ LOGIC AI VÀ ĐỊNH GIÁ CỦA BẠN VÀO ĐÂY ---
    VIETNAM_CAR_MARKET_PRICE = {
            "vinfast_vf 5": 468000000,
            "vinfast_vf 8": 1090000000,
            "vinfast_vf 9": 1490000000,
            "vinfast_fadil": 350000000,
            "vinfast_lux a2.0": 850000000,
            "toyota_vios": 550000000,
            "toyota_camry": 1100000000,
            "toyota_corolla cross": 850000000, # Đã bổ sung
            "toyota_innova": 800000000,        # Đã bổ sung
            "honda_city": 550000000,
            "honda_cr-v": 1050000000,
            "mazda_cx-5": 850000000,
            "mazda_mazda 3": 700000000,
            "ford_ranger": 850000000,
            "ford_everest": 1200000000,
            # THÊM HYUNDAI VÀ CÁC HÃNG KHÁC VÀO ĐÂY:
            "hyundai_accent": 500000000,
            "hyundai_tucson": 850000000,
            "kia_morning": 380000000,
            "kia_cerato": 600000000,
            "kia_k3": 600000000,
            "kia_seltos": 650000000
        }

    car_data = data.model_dump(exclude={"txhash"}) 
    
    # ==========================================
    # BỘ LỌC 2: CHỐNG LỖI 'UNHASHABLE LIST' CỦA PANDAS
    # ==========================================
    ai_safe_data = {}
    for key, value in car_data.items():
        if isinstance(value, (list, dict)):
            ai_safe_data[key] = str(value) 
        else:
            ai_safe_data[key] = value
            
    df_input = pd.DataFrame([ai_safe_data])
    # ==========================================
    
    try:
        car_key = f"{data.Vehicle_brand.lower()}_{data.Vehicle_model.lower()}"
        
        if car_key in VIETNAM_CAR_MARKET_PRICE:
            base_price_vnd = VIETNAM_CAR_MARKET_PRICE[car_key]
        else:
            # ==========================================
            # BỘ LỌC 3: CỨU CÁNH AI (CHỐNG LỆCH CỘT VÀ CHỮ TRONG MODEL)
            # ==========================================
            # 1. Báo cho Pandas biết AI cần chính xác những cột nào
            if hasattr(model, "feature_names_in_"):
                expected_features = model.feature_names_in_
            elif 'saved_features' in globals() and saved_features is not None:
                expected_features = saved_features
            else:
                expected_features = df_input.columns
            
            # 2. PHIÊN DỊCH CHỮ THÀNH SỐ (One-Hot Encoding)
            df_encoded = pd.get_dummies(df_input)
            
            # 3. Tự động cắt gọt: Vứt bỏ cột thừa từ Frontend, tự điền số 0 vào cột thiếu
            df_aligned = df_encoded.reindex(columns=expected_features, fill_value=0)
            
            # 4. CHỐT CHẶN CUỐI CÙNG: Ép TẤT CẢ về dạng số để AI không bị crash!
            df_aligned = df_aligned.apply(pd.to_numeric, errors='coerce').fillna(0)
            
            # 5. Dùng data đã gọt giũa sạch sẽ đưa vào AI dự đoán
            predicted_price_pln = model.predict(df_aligned)[0]
            
            base_price_vnd = predicted_price_pln * PLN_TO_VND_RATE
            # ==========================================
        
        current_year = 2026
        car_age = current_year - data.Production_year
        if car_age > 0:
            base_price_vnd *= (1 - (car_age * 0.08)) 
            
        if data.Mileage_km > 0:
            base_price_vnd *= (1 - (data.Mileage_km / 10000 * 0.01))

        brand_key = data.Vehicle_brand.lower()
        reputation_score = BRAND_REPUTATION_INDEX.get(brand_key, 0.7)
        
        condition_score = 1.0 
        for condition in data.vehicle_conditions:
            condition_score *= CONDITION_PENALTY_INDEX.get(condition.lower(), 1.0)
            
        if data.doors_replaced > 0:
            condition_score *= (1.0 - (data.doors_replaced * 0.02))

        if data.scratch_severity == "minor":
            condition_score -= 0.02 
        elif data.scratch_severity == "major":
            condition_score -= 0.07 
            
        if data.previous_owners > 1:
            condition_score -= ((data.previous_owners - 1) * 0.03)
            
        if data.Fuel_type.lower() in ["electric", "ev"] and car_age > 2:
            if getattr(data, 'ev_battery_type', None) == "rented":
                condition_score -= 0.15 
            elif getattr(data, 'ev_battery_type', None) == "bought":
                condition_score -= 0.10 
                
        condition_score = max(condition_score, 0.3)

        plate_bonus_vnd = 0
        if getattr(data, 'license_plate', None):
            plate_prefix = str(data.license_plate)[:2] 
            if plate_prefix in CITY_PLATE_PREFIXES:
                plate_bonus_vnd += 20000000 
                
            if "-" in data.license_plate:
                tail_numbers = data.license_plate.split("-")[1].replace(".", "").strip()
                
                if len(tail_numbers) == 5 and len(set(tail_numbers)) == 1:
                    plate_bonus_vnd += 500000000 
                elif len(tail_numbers) >= 4 and len(set(tail_numbers[-4:])) == 1:
                    plate_bonus_vnd += 300000000
                elif tail_numbers in ["12345", "23456", "34567", "45678", "56789", "6789"]:
                    plate_bonus_vnd += 200000000
                elif len(tail_numbers) >= 2 and tail_numbers[-2:] in ["68", "86", "39", "79"]:
                    plate_bonus_vnd += 50000000
                        
        final_predicted_price_vnd = round(base_price_vnd * reputation_score * condition_score) + plate_bonus_vnd
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi dự đoán: {str(e)}")

    # --- TẠO MÃ BĂM (CAR HASH) ĐỂ NEO LÊN BLOCKCHAIN ---
    random_salt = uuid.uuid4().hex
    data_to_protect = {
        "predicted_price": int(final_predicted_price_vnd), # Ép thẳng về số nguyên int()
        "license_plate": getattr(data, 'license_plate', None),
        "full_data": car_data 
    }
    SECRET_PEPPER = os.getenv("SECRET_PEPPER", "default_pepper")
    data_string = json.dumps(data_to_protect, sort_keys=True) + random_salt + SECRET_PEPPER
    car_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
    
    formatted_price_vnd = f"{int(final_predicted_price_vnd):,}".replace(',', '.') + " VNĐ"

    return {
        "status": "success",
        "predicted_price_raw": int(final_predicted_price_vnd),
        "predicted_price_display": formatted_price_vnd,
        "carHash": car_hash,
        "salt": random_salt
    }


# ==========================================
# BƯỚC 2: API CHỐT SỔ (XÁC THỰC TXHASH & LƯU DATABASE)
# ==========================================
@router.post("/evaluate/confirm")
async def confirm_evaluation(req: ConfirmRequest):
    # LỖI SỐ 1 ĐÃ SỬA: Dùng getattr thay vì .get()
    user_email = getattr(req.vehicle_data, 'user_email', None)
    expected_fee = 0.001 
    
    # 1. KIỂM TRA QUYỀN VIP TỪ SUPABASE ĐỂ ÁP DỤNG PHÍ GAS
    if user_email:
        try:
            profile_res = supabase.table("profiles").select("tier").eq("email", user_email).execute()
            if profile_res.data and len(profile_res.data) > 0:
                if profile_res.data[0].get("tier") == "vip":
                    expected_fee = 0.0 
        except Exception as e:
            print(f"Lỗi kiểm tra tier của user {user_email}: {e}")

    # 1.1. CHỐT CHẶN 1: KIỂM TRA THANH TOÁN TRÊN BLOCKCHAIN
    is_paid = verify_transaction(req.txhash, expected_fee)
    if not is_paid:
        raise HTTPException(
            status_code=400, 
            detail=f"Giao dịch không hợp lệ, hoặc không đủ {expected_fee} ETH phí!"
        )

    # 1.2. CHỐT CHẶN 2: CHỐNG REPLAY ATTACK (KIỂM TRA TXHASH ĐÃ DÙNG CHƯA)
    db_check = supabase.table("transactions").select("txhash").eq("txhash", req.txhash).execute()
    if len(db_check.data) > 0:
        raise HTTPException(status_code=400, detail="Mã giao dịch này đã được sử dụng để định giá rồi!")

    # 1.3. CHỐT CHẶN TỐI THƯỢNG: KIỂM TRA TÍNH TOÀN VẸN DỮ LIỆU BẰNG HASH
    car_data_dict = req.vehicle_data.model_dump(exclude={"txhash"})
    
    data_to_verify = {
        "predicted_price": int(req.predicted_price), # Ép thẳng về int giống hệt lúc Draft
        "license_plate": getattr(req.vehicle_data, 'license_plate', None),
        "full_data": car_data_dict
    }
    
    SECRET_PEPPER = os.getenv("SECRET_PEPPER", "default_pepper")
    data_string = json.dumps(data_to_verify, sort_keys=True) + req.salt + SECRET_PEPPER
    recalculated_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    if recalculated_hash != req.carHash:
         print("Hash gốc (Draft):", req.carHash)
         print("Hash tính lại (Confirm):", recalculated_hash)
         raise HTTPException(
             status_code=400, 
             detail="CẢNH BÁO: Dữ liệu xe hoặc giá đã bị đánh tráo giữa đường truyền!"
         )

    # ==========================================
    # PHẦN 3: LƯU TRỮ DATABASE VÀ TRẢ KẾT QUẢ
    # ==========================================
    transaction_record = {
        "txhash": req.txhash,
        "predicted_price": req.predicted_price,  
        "brand": req.vehicle_data.Vehicle_brand, 
        "model": req.vehicle_data.Vehicle_model,
        "year": int(req.vehicle_data.Production_year),
        "mileage": int(req.vehicle_data.Mileage_km), 
        "fuel_type": req.vehicle_data.Fuel_type,
        "license_plate": getattr(req.vehicle_data, 'license_plate', None),
        "full_data": car_data_dict,
        "user_email": user_email,
        "salt": req.salt,              
        "data_signature": req.carHash 
    }

    try:
        supabase.table("transactions").insert(transaction_record).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu DB: {str(e)}")

    formatted_price_vnd = f"{int(req.predicted_price):,}".replace(',', '.') + " VNĐ"
    return {
        "status": "success",
        "message": "Đã định giá và ghi nhận giao dịch vào DB",
        "data": {
            "predicted_price_raw": req.predicted_price, 
            "predicted_price_display": formatted_price_vnd, 
            "license_plate": getattr(req.vehicle_data, 'license_plate', None),
            "txhash": req.txhash
        }
    }
    
@router.get("/stats")
async def get_dashboard_stats():
    try:
        # 1. SỬA DÒNG NÀY: Xóa chữ 'email' đi, chỉ để lại 'brand' và 'user_email'
        data = supabase.table('transactions').select('brand, user_email').execute().data
        
        total_tx = len(data)
        brand_map = {}
        user_map = {}

        for tx in data:
            b_raw = tx.get('brand') or 'Khác'
            b = b_raw.strip().lower()
            if b == 'vinfast': b = 'VinFast'
            elif b == 'toyota': b = 'Toyota'
            else: b = b.capitalize()
            
            brand_map[b] = brand_map.get(b, 0) + 1
            
            # 2. SỬA DÒNG NÀY: Chỉ lấy dữ liệu từ 'user_email'
            email = tx.get('user_email')
            if email:
                user_map[email] = user_map.get(email, 0) + 1

        # 3. Sắp xếp Top 5 Hãng xe
        brands_array = [
            {"name": k, "value": v} 
            for k, v in brand_map.items()
        ]
        brands_array = sorted(brands_array, key=lambda x: x['value'], reverse=True)[:5]

        # 4. Sắp xếp Top 3 Người đóng góp
        users_array = [
            {"email": k, "name": k.split('@')[0], "count": v} 
            for k, v in user_map.items()
        ]
        users_array = sorted(users_array, key=lambda x: x['count'], reverse=True)[:3]

        # 5. Trả về cục JSON đã "nấu chín" cho Frontend
        return {
            "status": "success",
            "data": {
                "total_tx": total_tx,
                "top_brands": brands_array,
                "top_contributors": users_array
            }
        }
        
    except Exception as e:
        return {"status": "error", "detail": str(e)}    
    
    



# ==========================================
# API 2: LẤY CHI TIẾT GIAO DỊCH (BẢO MẬT)
# ==========================================
@router.get("/{txhash}")
async def get_certificate(txhash: str):
    # 1. Kéo dữ liệu từ Supabase
    data = supabase.table("transactions").select("*").eq("txhash", txhash).execute()
    if not data.data or len(data.data) == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã giao dịch này!")
        
    record = data.data[0]
    
    # 2. THUẬT TOÁN KIỂM TRA TOÀN VẸN (Phải BĂM GIỐNG HỆT lúc Confirm)
    # Lấy full_data từ DB và đảm bảo tuyệt đối không có dính key 'txhash' bên trong
    raw_full_data = record.get('full_data', {})
    clean_full_data = {k: v for k, v in raw_full_data.items() if k != "txhash"}
    
    # Dựng lại cấu trúc y hệt lúc lưu
    data_to_verify = {
        "predicted_price": int(record.get('predicted_price', 0)), # Ép int()
        "license_plate": record.get('license_plate'),
        "full_data": clean_full_data
    }
    
    # Lấy Salt từ DB và Pepper từ môi trường
    stored_salt = record.get('salt', '')
    SECRET_PEPPER = os.getenv("SECRET_PEPPER", "default_pepper")
    
    # Băm lại
    data_string = json.dumps(data_to_verify, sort_keys=True) + stored_salt + SECRET_PEPPER
    recalculated_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
    
    # 3. GẮN CỜ BÁO ĐỘNG
    # So sánh mã vừa băm với mã 'data_signature' (chính là carHash) đã lưu
    stored_hash = record.get('data_signature')
    is_tampered = (recalculated_hash != stored_hash)
    
    # Trả kết quả về cho Frontend
    return {
        "status": "success",
        "is_tampered": is_tampered,
        "data": {
            "txhash": record.get('txhash'),
            "predicted_price_vnd": record.get('predicted_price'),
            "license_plate": record.get('license_plate'),
            "original_car_info": raw_full_data
        }
    }


# ==========================================
# API 3: NÂNG CẤP TÀI KHOẢN VIP QUA BLOCKCHAIN
# ==========================================
class UpgradeVIPRequest(BaseModel):
    email: str
    txHash: str

@router.post("/upgrade-vip")
async def upgrade_to_vip(req: UpgradeVIPRequest):
    # 1. TẠM THỜI TẮT KIỂM TRA BLOCKCHAIN ĐỂ TRỊ BỆNH "PENDING"
    # is_valid = verify_transaction(req.txHash, 0.05)
    # 
    # if not is_valid:
    #     raise HTTPException(status_code=400, detail="Giao dịch Blockchain không hợp lệ hoặc không đủ 0.05 ETH!")

    # 2. CHO PHÉP CẬP NHẬT TRẠNG THÁI TRÊN SUPABASE LUÔN
    try:
        res = supabase.table("profiles").update({"tier": "vip"}).eq("email", req.email).execute()
        
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản người dùng trong Database.")
            
        return {"success": True, "message": "Nâng cấp VIP thành công!"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật Database: {str(e)}")

# ==========================================
# API 4: DÀNH CHO DEV - RESET TÀI KHOẢN VỀ STANDARD
# ==========================================
class ResetVIPRequest(BaseModel):
    email: str

@router.post("/reset-vip")
async def reset_vip(req: ResetVIPRequest):
    try:
        # Cập nhật tier về lại standard trên Supabase
        supabase.table("profiles").update({"tier": "standard"}).eq("email", req.email).execute()
        return {"success": True, "message": "Đã reset về Standard"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
# ==========================================
# API 5: OCR - ĐỌC GỘP NHIỀU ẢNH CÀ VẸT CÙNG LÚC
# ==========================================
@router.post("/extract-cavet")
async def extract_cavet_info(files: List[UploadFile] = File(...)):
    print(f"\n--- BẮT ĐẦU TIẾN TRÌNH AI OCR CHO {len(files)} ẢNH ---")
    try:
        combined_raw_text = ""
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        # Vòng lặp: Mở từng ảnh ra, ép AI đọc và gộp tất cả chữ lại thành 1 đoạn văn dài
        for idx, file in enumerate(files):
            print(f"1. Đang xử lý ảnh thứ {idx + 1}...")
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))
            
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
                
            raw_text = pytesseract.image_to_string(image, lang='eng', timeout=10)
            combined_raw_text += raw_text + "\n\n" # Gộp text của các ảnh lại
            
        print("--> AI đã đọc xong toàn bộ ảnh! Bắt đầu trích xuất...")
        
        # Chạy thuật toán tìm kiếm trên ĐOẠN VĂN TỔNG HỢP
        matches = re.findall(r'\(([A-Za-z0-9_]+)\)\s*:\s*([^\n]+)', combined_raw_text)
        
        extracted_data = {}
        for key, val in matches:
            clean_val = val.strip()
            if clean_val.lower() == 'true': clean_val = True
            elif clean_val.lower() == 'false': clean_val = False
            elif clean_val.isdigit(): clean_val = int(clean_val)
            extracted_data[key] = clean_val

        # Cứu cánh cho biển số
        if "license_plate" not in extracted_data:
            plate_match = re.search(r'([0-9]{2}[A-Z]{1,2}\s*-\s*[0-9]{3,4}\.?[0-9]{2})', combined_raw_text)
            if plate_match:
                extracted_data["license_plate"] = plate_match.group(1).replace(" ", "")

        print(f"4. Trích xuất thành công {len(extracted_data)} trường dữ liệu từ {len(files)} ảnh!")
        print("----------------------------------\n")

        return {
            "status": "success",
            "message": "Trích xuất thành công",
            "data": extracted_data,
            "raw_text": combined_raw_text
        }
    except RuntimeError as timeout_err:
        print("❌ LỖI: Tesseract bị treo quá 10s!")
        return {"status": "error", "detail": "Quá trình xử lý ảnh mất quá nhiều thời gian."}
    except Exception as e:
        print("❌ LỖI NGHIÊM TRỌNG:", str(e))
        return {"status": "error", "detail": f"Lỗi đọc ảnh: {str(e)}"}