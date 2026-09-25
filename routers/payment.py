from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/v1/payment", tags=["Payment"])

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PRICE_PER_TOKEN = 80000  # 80.000 VNĐ cho mỗi lượt định giá

class CreateInvoiceRequest(BaseModel):
    user_id: str
    token_amount: int

@router.post("/create-invoice")
async def create_deposit_invoice(req: CreateInvoiceRequest):
    if req.token_amount <= 0:
        raise HTTPException(status_code=400, detail="Số token nạp không hợp lệ")
        
    total_amount = req.token_amount * PRICE_PER_TOKEN
    # Tạo mã dạng: NAP_123456_5TK (Lấy 6 ký tự đầu của UUID)
    short_uid = req.user_id.replace("-", "")[:6].upper()
    invoice_code = f"NAP{short_uid}{req.token_amount}TK"
    
    # Lưu hóa đơn nạp vào cơ sở dữ liệu
    record = supabase.table("deposit_invoices").insert({
        "user_id": req.user_id,
        "invoice_code": invoice_code,
        "token_amount": req.token_amount,
        "total_vnd": total_amount,
        "status": "PENDING"
    }).execute()
    
    return {
        "invoice_code": invoice_code,
        "total_amount": total_amount,
        "token_amount": req.token_amount
    }

# Webhook nhận biến động số dư từ SePay
@router.post("/webhook/bank-transfer")
async def handle_bank_webhook(payload: dict):
    # Dựa theo format SePay
    transfer_content = payload.get("content", "")
    transfer_amount = payload.get("transferAmount", 0)
    
    # Tìm mã hóa đơn (NAP...) trong nội dung chuyển khoản
    import re
    match = re.search(r"NAP[A-Z0-9]+TK", transfer_content.upper())
    if not match:
        return {"status": "ignored", "message": "Không tìm thấy cú pháp hóa đơn trong nội dung"}
        
    invoice_code = match.group(0)
    
    # Truy vấn hóa đơn chưa thanh toán tương ứng
    res = supabase.table("deposit_invoices")\
        .select("*")\
        .eq("invoice_code", invoice_code)\
        .eq("status", "PENDING")\
        .execute()
        
    if not res.data:
        return {"status": "ignored", "message": "Không tìm thấy hóa đơn phù hợp hoặc đã thanh toán"}
        
    invoice = res.data[0]
    
    if transfer_amount < invoice["total_vnd"]:
        # Chuyển khoản thiếu tiền, có thể log lại hoặc đổi status thành PARTIAL
        raise HTTPException(status_code=400, detail="Số tiền thanh toán không đủ")
        
    # Đánh dấu hóa đơn hoàn tất và cộng số dư tài khoản
    supabase.table("deposit_invoices").update({"status": "SUCCESS"}).eq("id", invoice["id"]).execute()
    
    supabase.rpc("increment_user_balance", {
        "uid": invoice["user_id"],
        "val": invoice["token_amount"]
    }).execute()
    
    return {"status": "ok", "message": "Nạp tín dụng thành công"}
