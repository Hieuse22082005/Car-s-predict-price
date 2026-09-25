import os

with open('routers/transactions.py', 'r', encoding='utf-8') as f:
    text = f.read()

sponsored_code = """
class SponsoredValuationRequest(BaseModel):
    user_id: str
    vehicle_data: CarValuationRequest

@router.post("/evaluate/sponsored")
async def evaluate_sponsored(req: SponsoredValuationRequest):
    # 1. Deduct token
    try:
        profile_res = supabase.table("profiles").select("token_balance").eq("id", req.user_id).execute()
        if not profile_res.data or profile_res.data[0].get("token_balance", 0) < 1:
            raise HTTPException(status_code=400, detail="Số dư tài khoản không đủ. Vui lòng nạp thêm token!")
            
        supabase.rpc("increment_user_balance", {
            "uid": req.user_id,
            "val": -1
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi kiểm tra số dư: {str(e)}")

    # 2. Run AI Logic (Reuse draft logic manually)
    data = req.vehicle_data
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
            "toyota_corolla cross": 850000000,
            "toyota_innova": 800000000,
            "honda_city": 550000000,
            "honda_cr-v": 1050000000,
            "mazda_cx-5": 850000000,
            "mazda_mazda 3": 700000000,
            "ford_ranger": 850000000,
            "ford_everest": 1200000000,
            "hyundai_accent": 500000000,
            "hyundai_tucson": 850000000,
            "kia_morning": 380000000,
            "kia_cerato": 600000000,
            "kia_k3": 600000000,
            "kia_seltos": 650000000
    }
    car_data = data.model_dump(exclude={"txhash"}) 
    ai_safe_data = {}
    for key, value in car_data.items():
        if isinstance(value, (list, dict)):
            ai_safe_data[key] = str(value) 
        else:
            ai_safe_data[key] = value
            
    df_input = pd.DataFrame([ai_safe_data])
    try:
        car_key = f"{data.Vehicle_brand.lower()}_{data.Vehicle_model.lower()}"
        if car_key in VIETNAM_CAR_MARKET_PRICE:
            base_price_vnd = VIETNAM_CAR_MARKET_PRICE[car_key]
        else:
            if hasattr(model, "feature_names_in_"):
                expected_features = model.feature_names_in_
            elif 'saved_features' in globals() and saved_features is not None:
                expected_features = saved_features
            else:
                expected_features = df_input.columns
            df_encoded = pd.get_dummies(df_input)
            df_aligned = df_encoded.reindex(columns=expected_features, fill_value=0)
            df_aligned = df_aligned.apply(pd.to_numeric, errors='coerce').fillna(0)
            predicted_price_pln = model.predict(df_aligned)[0]
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
        for condition in getattr(data, 'vehicle_conditions', []):
            condition_score *= CONDITION_PENALTY_INDEX.get(condition.lower(), 1.0)
            
        if getattr(data, 'doors_replaced', 0) > 0:
            condition_score *= (1.0 - (data.doors_replaced * 0.02))

        if getattr(data, 'scratch_severity', '') == "minor":
            condition_score -= 0.02 
        elif getattr(data, 'scratch_severity', '') == "major":
            condition_score -= 0.07 
            
        if getattr(data, 'previous_owners', 1) > 1:
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

    random_salt = uuid.uuid4().hex
    data_to_protect = {
        "predicted_price": int(final_predicted_price_vnd),
        "license_plate": getattr(data, 'license_plate', None),
        "full_data": car_data 
    }
    SECRET_PEPPER = os.getenv("SECRET_PEPPER", "default_pepper")
    data_string = json.dumps(data_to_protect, sort_keys=True) + random_salt + SECRET_PEPPER
    car_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
    
    # 3. Luu vao CSDL, dat chain_status = QUEUED
    transaction_record = {
        "user_id": req.user_id,
        "chain_status": "QUEUED",
        "predicted_price": int(final_predicted_price_vnd),  
        "brand": data.Vehicle_brand, 
        "model": data.Vehicle_model,
        "year": int(data.Production_year),
        "mileage": int(data.Mileage_km), 
        "fuel_type": data.Fuel_type,
        "license_plate": getattr(data, 'license_plate', None),
        "full_data": car_data,
        "user_email": getattr(data, 'user_email', None),
        "user_signature": getattr(data, 'user_signature', None),
        "salt": random_salt,              
        "car_signature": car_hash # Dùng để Worker ký gửi lên Sepolia
    }

    try:
        supabase.table("transactions").insert(transaction_record).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu DB: {str(e)}")

    formatted_price_vnd = f"{int(final_predicted_price_vnd):,}".replace(',', '.') + " VND"
    return {
        "status": "success",
        "predicted_price_raw": int(final_predicted_price_vnd),
        "predicted_price_display": formatted_price_vnd,
        "carHash": car_hash,
        "salt": random_salt,
        "chain_status": "QUEUED"
    }

# ==========================================
"""

if "SponsoredValuationRequest" not in text:
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('@router.post("/evaluate/draft")'):
            lines.insert(i, sponsored_code)
            break
            
    with open('routers/transactions.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("Injected sponsored endpoint")
else:
    print("Already injected")
