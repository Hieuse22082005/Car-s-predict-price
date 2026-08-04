from fastapi import APIRouter, HTTPException
from schemas import CarValuationRequest
import joblib
import pandas as pd
import os

router = APIRouter()

# Tải mô hình AI khi Router được khởi tạo
MODEL_PATH = "ml_models/car_pricing_model.pkl"
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

@router.post("/evaluate")
async def evaluate_and_save_transaction(data: CarValuationRequest):
    if not model:
        raise HTTPException(status_code=500, detail="Mô hình AI chưa được khởi tạo trên Backend.")

    # 1. Tách txhash ra, phần còn lại chuyển thành DataFrame cho AI
    # Dùng model_dump() cho Pydantic v2 (hoặc dict() cho v1)
    car_data = data.model_dump(exclude={"txhash"}) 
    
    # Chuyển đổi thành cấu trúc DataFrame 1 dòng
    df_input = pd.DataFrame([car_data])

    # 2. Dự đoán giá xe bằng mô hình KNN
    try:
        predicted_price = model.predict(df_input)[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi khi dự đoán: {str(e)}")

    # 3. Logic lưu trữ vào Cơ sở dữ liệu (Supabase)
    # Lúc này bạn đã có trọn bộ: Dữ liệu xe, Giá dự đoán (predicted_price), và txhash
    transaction_record = {
        **car_data,
        "predicted_price": float(predicted_price),
        "txhash": data.txhash
    }
    
    # TODO: Khai báo Supabase client và lưu transaction_record vào database
    # supabase.table("transactions").insert(transaction_record).execute()

    # 4. Trả kết quả về cho Frontend
    return {
        "status": "success",
        "message": "Đã định giá và ghi nhận giao dịch thành công",
        "data": {
            "predicted_price": float(predicted_price),
            "txhash": data.txhash
        }
    }