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

if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

PLN_TO_VND_RATE = 7040.57


# ==========================================
# API 1: ĐỊNH GIÁ XE & KIỂM TRA PHÍ (0 HOẶC 0.001 ETH)
# ==========================================
@router.post("/evaluate")
async def evaluate_and_save_transaction(data: CarValuationRequest):
    # 1. KIỂM TRA QUYỀN VIP TỪ SUPABASE ĐỂ ÁP DỤNG PHÍ GAS
    user_email = getattr(data, 'user_email', None)
    expected_fee = 0.001 
    
    if user_email:
        try:
            profile_res = supabase.table("profiles").select("tier").eq("email", user_email).execute()
            if profile_res.data and len(profile_res.data) > 0:
                if profile_res.data[0].get("tier") == "vip":
                    expected_fee = 0.0 
        except Exception as e:
            print(f"Lỗi kiểm tra tier của user {user_email}: {e}")

    # 1.1. CHỐT CHẶN 1: KIỂM TRA THANH TOÁN TRÊN BLOCKCHAIN
    is_paid = verify_transaction(data.txhash, expected_fee)
    if not is_paid:
        raise HTTPException(
            status_code=400, 
            detail=f"Giao dịch không hợp lệ, hoặc không đủ {expected_fee} ETH phí!"
        )

    # 1.2. CHỐT CHẶN 2: CHỐNG REPLAY ATTACK 
    try:
        db_check = supabase.table("transactions").select("txhash").eq("txhash", data.txhash).execute()
        if len(db_check.data) > 0:
            raise HTTPException(
                status_code=400, 
                detail="Mã giao dịch này đã được sử dụng để định giá rồi!"
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Lỗi kiểm tra lịch sử giao dịch: {str(e)}")

    # ==========================================
    # PHẦN 2: LOGIC AI VÀ ĐỊNH GIÁ XE
    # ==========================================
    if not model:
        raise HTTPException(status_code=500, detail="Mô hình AI chưa khởi tạo.")

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
        car_key = f"{data.Vehicle_brand.lower()}_{data.Vehicle_model.lower()}"
        
        if car_key in VIETNAM_CAR_MARKET_PRICE:
            base_price_vnd = VIETNAM_CAR_MARKET_PRICE[car_key]
        else:
            predicted_price_pln = model.predict(df_input)[0]
            base_price_vnd = predicted_price_pln * PLN_TO_VND_RATE
        
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
            if data.ev_battery_type == "rented":
                condition_score -= 0.15 
            elif data.ev_battery_type == "bought":
                condition_score -= 0.10 
                
        condition_score = max(condition_score, 0.3)

        plate_bonus_vnd = 0
        if data.license_plate:
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
        formatted_price_vnd = f"{int(final_predicted_price_vnd):,}".replace(',', '.') + " VNĐ"
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi dự đoán: {str(e)}")

    # ==========================================
    # PHẦN 3: LƯU TRỮ DATABASE VÀ TRẢ KẾT QUẢ
    # ==========================================
    random_salt = uuid.uuid4().hex
    data_to_protect = {
        "txhash": data.txhash,
        "predicted_price": final_predicted_price_vnd,
        "license_plate": data.license_plate,
        "full_data": data.model_dump() 
    }
    SECRET_PEPPER = os.getenv("SECRET_PEPPER", "default_pepper")
    data_string = json.dumps(data_to_protect, sort_keys=True) + random_salt + SECRET_PEPPER
    data_signature = hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    transaction_record = {
        "txhash": data.txhash,
        "predicted_price": final_predicted_price_vnd,  
        "brand": data.Vehicle_brand,
        "model": data.Vehicle_model,
        "year": int(data.Production_year),
        "mileage": int(data.Mileage_km), 
        "fuel_type": data.Fuel_type,
        "license_plate": data.license_plate,
        "full_data": data.model_dump(), 
        "user_email": getattr(data, 'user_email', None) or car_data.get('user_email'),
        "salt": random_salt,              
        "data_signature": data_signature  
    }

    try:
        db_response = supabase.table("transactions").insert(transaction_record).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu DB: {str(e)}")

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


# ==========================================
# API 2: LẤY CHI TIẾT GIAO DỊCH (BẢO MẬT)
# ==========================================
@router.get("/{txhash}")
async def get_transaction_details(txhash: str):
    try:
        db_response = supabase.table("transactions").select("*").eq("txhash", txhash).execute()
        
        if not db_response.data or len(db_response.data) == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"Không tìm thấy dữ liệu xe với mã txhash: {txhash}"
            )
            
        record = db_response.data[0]
        
        stored_salt = record.get("salt")
        stored_signature = record.get("data_signature")
        is_tampered = False
        
        if stored_salt and stored_signature:
            current_data = {
                "txhash": record.get("txhash"),
                "predicted_price": record.get("predicted_price"),
                "license_plate": record.get("license_plate"),
                "full_data": record.get("full_data")
            }
            SECRET_PEPPER = os.getenv("SECRET_PEPPER", "default_pepper")
            current_string = json.dumps(current_data, sort_keys=True) + stored_salt + SECRET_PEPPER
            current_signature = hashlib.sha256(current_string.encode('utf-8')).hexdigest()
            
            if current_signature != stored_signature:
                is_tampered = True
        
        return {
            "status": "success",
            "message": "Lấy thông tin xe thành công",
            "is_tampered": is_tampered, 
            "data": {
                "id": record.get("id"),
                "created_at": record.get("created_at"),
                "txhash": record.get("txhash"),
                "license_plate": record.get("license_plate"),
                "predicted_price_vnd": record.get("predicted_price"),
                "original_car_info": record.get("full_data") 
            }
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Lỗi truy xuất dữ liệu: {str(e)}")


# ==========================================
# API 3: NÂNG CẤP TÀI KHOẢN VIP QUA BLOCKCHAIN
# ==========================================
class UpgradeVIPRequest(BaseModel):
    email: str
    txHash: str

@router.post("/upgrade-vip")
async def upgrade_to_vip(req: UpgradeVIPRequest):
    # 1. KIỂM TRA GIAO DỊCH TRÊN BLOCKCHAIN VỚI MỨC PHÍ 0.05 ETH
    is_valid = verify_transaction(req.txHash, 0.05)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Giao dịch Blockchain không hợp lệ hoặc không đủ 0.05 ETH!")

    # 2. CẬP NHẬT TRẠNG THÁI TRÊN SUPABASE
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