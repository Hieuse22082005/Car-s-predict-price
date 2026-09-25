from database import supabase

new_cars = [
    {
        "brand": "Mercedes-Benz",
        "model": "AMG G 63",
        "condition": "Mới 100%",
        "manufacture_year": 2024,
        "buy_price": 150000,
        "sell_price": 180000,
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1520031441872-265e4ff70366?auto=format&fit=crop&q=80&w=1200",
        "description": "Biểu tượng của sự quyền lực và sang trọng. Động cơ V8 Biturbo mạnh mẽ cùng thiết kế hình khối vượt thời gian."
    },
    {
        "brand": "Porsche",
        "model": "911 GT3",
        "condition": "Mới 100%",
        "manufacture_year": 2024,
        "buy_price": 250000,
        "sell_price": 280000,
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1503376760367-15ea4dac6b03?auto=format&fit=crop&q=80&w=1200",
        "description": "Chiếc xe đua đường phố hoàn hảo. Khí động học đỉnh cao và âm thanh động cơ hút khí tự nhiên đầy mê hoặc."
    },
    {
        "brand": "Audi",
        "model": "RS e-tron GT",
        "condition": "Mới 100%",
        "manufacture_year": 2024,
        "buy_price": 130000,
        "sell_price": 150000,
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1614200179396-2bdb77ebf81b?auto=format&fit=crop&q=80&w=1200",
        "description": "Tương lai của xe hiệu suất cao. Mẫu xe thuần điện mang lại trải nghiệm tăng tốc nghẹt thở và thiết kế cuốn hút."
    },
    {
        "brand": "BMW",
        "model": "M8 Competition",
        "condition": "Xe Lướt",
        "manufacture_year": 2023,
        "buy_price": 110000,
        "sell_price": 135000,
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1555353540-64fd8b028bfb?auto=format&fit=crop&q=80&w=1200",
        "description": "Sự kết hợp hoàn mỹ giữa mẫu xe coupe hạng sang cỡ lớn và sức mạnh bùng nổ của bộ phận BMW M."
    },
    {
        "brand": "Lexus",
        "model": "LC 500",
        "condition": "Xe Lướt",
        "manufacture_year": 2022,
        "buy_price": 85000,
        "sell_price": 95000,
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1623869675781-80aa31012a5a?auto=format&fit=crop&q=80&w=1200",
        "description": "Nghệ thuật thủ công Nhật Bản hội tụ cùng khối động cơ V8 5.0L hút khí tự nhiên hiếm hoi còn sót lại."
    }
]

try:
    response = supabase.table("showroom_cars").insert(new_cars).execute()
    print("Thêm thành công 5 xe!")
except Exception as e:
    print(f"Lỗi: {e}")
