import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from database import supabase

router = APIRouter()

class BookingRequest(BaseModel):
    carId: str = None
    carModel: str
    fullName: str
    phone: str
    email: str
    date: str
    time: str

def send_booking_email(to_email: str, full_name: str, car_model: str, date: str, time: str, phone: str):
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        print("Cảnh báo: Chưa cấu hình SMTP_EMAIL và SMTP_PASSWORD trong .env")
        return

    subject = f"Xác nhận đặt lịch xem xe - {car_model}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; line-height: 1.6; color: #333;">
        <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #d97706;">
            <h2 style="color: #d97706; margin: 0;">XÁC NHẬN ĐẶT LỊCH XEM XE</h2>
        </div>
        
        <div style="padding: 20px 0;">
            <p>Chào <strong>{full_name}</strong>,</p>
            <p>Cảm ơn bạn đã tin tưởng và đặt lịch xem xe tại showroom của chúng tôi. Hệ thống đã ghi nhận lịch hẹn của bạn với thông tin chi tiết như sau:</p>
            
            <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
            <p style="margin: 0 0 10px 0;">🚗 <strong>Xe đăng ký xem:</strong> <span style="color: #d97706; font-weight: bold;">{car_model}</span></p>
            <p style="margin: 0 0 10px 0;">📅 <strong>Ngày hẹn:</strong> {date}</p>
            <p style="margin: 0 0 10px 0;">⏰ <strong>Thời gian:</strong> {time}</p>
            <p style="margin: 0 0 10px 0;">📞 <strong>Số điện thoại của bạn:</strong> {phone}</p>
            <p style="margin: 0;">📍 <strong>Địa điểm:</strong> Showroom Auto, 123 Đường ABC, Quận XYZ, Hà Nội</p>
            </div>

            <p>Nếu có bất cứ thay đổi nào về lịch trình hoặc cần hỗ trợ thêm thông tin, xin vui lòng kết nối ngay với Hotline của chúng tôi: <strong style="color: #d97706; font-size: 18px;">0988.888.888</strong>.</p>
            <p>Chúng tôi rất mong được đón tiếp bạn tại showroom!</p>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 14px; color: #666; text-align: center;">
            <p style="margin: 0;">Trân trọng,</p>
            <p style="margin: 5px 0 0 0; font-weight: bold; color: #333;">Đội ngũ Auto Showroom</p>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = f"Auto Showroom <{smtp_email}>"
    msg['To'] = to_email

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(smtp_email, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f"Đã gửi email xác nhận cho {to_email}")
    except Exception as e:
        print(f"Lỗi khi gửi email: {str(e)}")

@router.post("")
def book_car_viewing(req: BookingRequest, background_tasks: BackgroundTasks):
    # 1. Lưu vào Supabase
    try:
        data = {
            "car_id": req.carId,
            "car_model": req.carModel,
            "customer_name": req.fullName,
            "phone": req.phone,
            "email": req.email,
            "booking_date": f"{req.date} {req.time}",
            "status": "pending"
        }
        response = supabase.table("car_bookings").insert(data).execute()
        
    except Exception as e:
        print("Lỗi lưu Supabase:", str(e))
        # Không fail request nếu Supabase có vấn đề nhỏ

    # 2. Đưa tác vụ gửi email vào chạy ngầm (Background Task) để không làm chậm API
    background_tasks.add_task(
        send_booking_email, 
        req.email, 
        req.fullName, 
        req.carModel, 
        req.date, 
        req.time, 
        req.phone
    )

    return {"success": True, "message": "Đặt lịch thành công, đang gửi email!"}
