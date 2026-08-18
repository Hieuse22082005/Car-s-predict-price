from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import supabase

router = APIRouter()

# Schema nhận dữ liệu từ Frontend
class OTPRequest(BaseModel):
    email: str
    fullName: str = ""
    phone: str = ""
    isRegister: bool = False

class VerifyRequest(BaseModel):
    email: str
    otp: str

@router.post("/send-otp", summary="Gửi mã OTP qua Email")
async def send_otp(req: OTPRequest):
    try:
        # Gọi Supabase gửi OTP
        res = supabase.auth.sign_in_with_otp({
            "email": req.email,
            "options": {
                "data": {
                    "display_name": req.fullName,
                    "phone": req.phone
                }
            }
        })
        return {"status": "success", "message": "Đã gửi mã OTP thành công!"}
    except Exception as e:
        print("LỖI GỬI OTP:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-otp", summary="Xác thực mã OTP")
async def verify_otp(req: VerifyRequest):
    try:
        # Xác thực mã OTP với Supabase
        res = supabase.auth.verify_otp({
            "email": req.email,
            "token": req.otp,
            "type": "email"
        })
        
        # Trả Token về cho Frontend lưu trữ
        return {
            "status": "success",
            "access_token": res.session.access_token,
            "user_email": res.user.email
        }
    except Exception as e:
        print("LỖI XÁC THỰC OTP:", str(e))
        raise HTTPException(status_code=401, detail="Mã OTP không hợp lệ hoặc đã hết hạn!")