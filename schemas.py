from pydantic import BaseModel
from typing import Optional, List
class CarValuationRequest(BaseModel):
    # Các trường dữ liệu số học
    Production_year: int
    Mileage_km: float
    Power_HP: float
    Displacement_cm3: float
    CO2_emissions: float
    Doors_number: int
    
    # Các trường dữ liệu phân loại (chữ)
    Condition: str
    Vehicle_brand: str
    Vehicle_model: str
    Vehicle_version: str
    Vehicle_generation: str
    Fuel_type: str
    Drive: str
    Transmission: str
    Type: str
    Colour: str
    Origin_country: str
    First_owner: str
    vehicle_conditions: List[str] = ["perfect"]
    # Thông tin Blockchain từ Frontend
    txhash: str# Mở file schemas.py và thêm đoạn này vào
    doors_replaced: int = 0            # Số cửa đã thay (0 đến 4)
    scratch_severity: str = "none"     # "none" (không xước), "minor" (xước dăm), "major" (móp méo nặng)
    previous_owners: int = 1           # Số đời chủ (1 là một chủ từ đầu)
    ev_battery_type: str = "none"
    license_plate: str = "Chưa có biển"
    user_email: Optional[str] = None
    user_signature: Optional[str] = None
    
    model_config = {"extra": "allow"}
class UserAuth(BaseModel):
    email: str
    password: str
    
class ChatRequest(BaseModel):
    message: str