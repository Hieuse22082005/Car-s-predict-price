from fastapi import APIRouter, HTTPException
from database import supabase
from pydantic import BaseModel

router = APIRouter()

class UpdateStatusRequest(BaseModel):
    status: str

@router.get("/")
def get_cars():
    try:
        response = supabase.table("showroom_cars").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{car_id}/status")
def update_car_status(car_id: str, request: UpdateStatusRequest):
    try:
        response = supabase.table("showroom_cars").update({"status": request.status}).eq("id", car_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
