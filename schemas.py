from pydantic import BaseModel

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
    
    # Thông tin Blockchain từ Frontend
    txhash: str