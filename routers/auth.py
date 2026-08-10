from fastapi import APIRouter, HTTPException
from schemas import UserAuth
from database import supabase

router = APIRouter()

@router.post("/register", summary="Đăng ký tài khoản mới")
async def register_user(user_data: UserAuth):
    print(f"--- ĐANG GỬI YÊU CẦU ĐĂNG KÝ ---")
    print(f"Email: {user_data.email}")
    print(f"Password: {user_data.password}")
    
    try:
        response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
        print("--- ĐĂNG KÝ THÀNH CÔNG ---")
        print(response)
        
        return {
            "status": "success", 
            "message": "Đăng ký thành công!",
            "user_id": response.user.id
        }
    except Exception as e:
        print("--- LỖI SUPABASE TỪ CHỐI ĐĂNG KÝ ---")
        print(str(e))
        raise HTTPException(status_code=400, detail=f"Lỗi đăng ký: {str(e)}")


@router.post("/login", summary="Đăng nhập hệ thống")
async def login_user(user_data: UserAuth):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        return {
            "status": "success", 
            "message": "Đăng nhập thành công!", 
            "access_token": response.session.access_token,
            "user_email": response.user.email
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không chính xác!")