from fastapi import APIRouter, HTTPException
from schemas import CarValuationRequest
from database import supabase
import joblib
import pandas as pd
import os

router = APIRouter()

MODEL_PATH = "ml_models/car_pricing_model.pkl"
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

@router.post("/evaluate")
async def evaluate_and_save_transaction(data: CarValuationRequest):
    if not model:
        raise HTTPException(status_code=500, detail="Mô hình AI chưa khởi tạo.")

    # 1. Dự đoán giá xe bằng mô hình KNN
    car_data = data.model_dump(exclude={"txhash"}) 
    df_input = pd.DataFrame([car_data])
    
    try:
        predicted_price = model.predict(df_input)[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi dự đoán: {str(e)}")

    # 2. Đóng gói dữ liệu (CHỈ LẤY CÁC CỘT CÓ TRONG ẢNH CỦA BẠN)
    # Lưu ý: Cột cuối cùng trong ảnh của bạn bị lấp một chút, có vẻ là "fuel_ty" hoặc "fuel_type".
    # Nếu trên DB của bạn là fuel_type thì nhớ sửa lại chữ fuel_ty ở dưới nhé!
    transaction_record = {
        "txhash": data.txhash,
        "predicted_price": float(predicted_price),
        "brand": data.Vehicle_brand,
        "model": data.Vehicle_model,
        "year": int(data.Production_year), # Ép kiểu về số nguyên
        "mileage": int(data.Mileage_km),   # Đổi từ 45000.0 thành 45000
        "fuel_type": data.Fuel_type  
    }

    print("--- DỮ LIỆU CHUẨN BỊ GỬI LÊN SUPABASE ---")
    print(transaction_record)

    # 3. Ghi nhận giao dịch vào cơ sở dữ liệu Supabase
    try:
        db_response = supabase.table("transactions").insert(transaction_record).execute()
        
        print("--- PHẢN HỒI TỪ SUPABASE ---")
        print(db_response)
        
    except Exception as e:
        print("--- LỖI SUPABASE TRẢ VỀ ---")
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Lỗi lưu DB: {str(e)}")

    # 4. Trả kết quả về cho Frontend
    return {
        "status": "success",
        "message": "Đã định giá và ghi nhận giao dịch vào DB",
        "data": {
            "predicted_price": float(predicted_price),
            "txhash": data.txhash
        }
    }