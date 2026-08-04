🚗 Hệ Thống Định Giá Xe Cũ Bảo Chứng Blockchain (Blockchain-Backed Car Valuation)

🌟 Tầm Nhìn Dự Án

Thị trường xe cũ luôn tồn tại sự e ngại về giá trị thực của phương tiện. Dự án này ra đời với mục tiêu trở thành **nền tảng định giá xe cũ uy tín hàng đầu và độc nhất**, nơi mỗi chiếc xe đều được đánh giá công bằng sát với giá thị trường.
Điểm khác biệt cốt lõi: Mọi kết quả định giá từ hệ thống đều được **bảo chứng bởi công ty** và **ghi nhận trực tiếp lên Smart Contract (Blockchain)**. Điều này đảm bảo tính độc nhất, minh bạch tuyệt đối và không thể bị chỉnh sửa bởi bất kỳ bên thứ ba nào, giúp người bán và người mua hoàn toàn an tâm giao dịch.
✨ Tính Năng Nổi Bật

* **🤖 Trí Tuệ Nhân Tạo (AI):** Ứng dụng mô hình Machine Learning (K-Nearest Neighbors) được huấn luyện trên tập dữ liệu lớn để đưa ra mức giá dự đoán sát với thị trường nhất.
* **⛓️ Bảo Chứng Bất Biến (Blockchain):** Mỗi giao dịch định giá đều được cấp một mã băm (`txhash`) duy nhất trên chuỗi khối, minh chứng cho sự tồn tại và tính vĩnh cửu của dữ liệu.
* **🛡️ Uy Tín Hàng Đầu:** Giấy chứng nhận định giá điện tử không thể làm giả, mang lại quyền lực đàm phán cho người bán.
* **⚡ Kiến Trúc Mở Rộng:** Backend được thiết kế dạng module với FastAPI, sẵn sàng mở rộng quy mô khi lượng người dùng tăng cao.

## ⚙️ Luồng Hoạt Động Của Hệ Thống (Workflow)
Hệ thống được thiết kế chặt chẽ giữa Giao diện người dùng (Frontend), Chuỗi khối (Blockchain) và Máy chủ xử lý (Backend):
1. **Thu thập thông số:** Người dùng nhập các thông tin chi tiết về tình trạng xe (năm sản xuất, số km, hãng, v.v.) trên Giao diện Frontend.
2. **Khởi tạo Smart Contract:** Frontend tương tác trực tiếp với Smart Contract để ghi nhận yêu cầu định giá và lấy về mã xác nhận giao dịch (`txhash`).
3. **Gửi dữ liệu định giá:** Frontend đóng gói toàn bộ thông số xe kèm theo `txhash` vừa nhận được và gửi lên Backend API.
4. **AI Xử lý & Dự đoán:** Backend tiếp nhận dữ liệu, sử dụng mô hình AI (KNN) đã qua huấn luyện để tính toán mức giá hợp lý nhất.
5. **Lưu trữ & Trả kết quả:** Dữ liệu xe, giá dự đoán và `txhash` được liên kết chặt chẽ và lưu vào cơ sở dữ liệu. Kết quả được trả về cho người dùng như một "Chứng thư định giá số" không thể chối cãi.

🛠️ Công Nghệ Sử Dụng
* **Backend:** Python, FastAPI, Pydantic (Validate dữ liệu).
* **Machine Learning:** Scikit-Learn (Mô hình KNN Regressor, StandardScaler, OneHotEncoder), Pandas.
* **Database:** Supabase / PostgreSQL.
* **Blockchain Integration:** Smart Contract, Web3 (Xử lý cấp `txhash` qua Frontend).

🚀 Hướng Dẫn Cài Đặt (Dành Cho Nhà Phát Triển)

**1. Clone dự án và thiết lập môi trường**

```bash
git clone <đường_dẫn_repo_của_bạn>
cd <thư_mục_dự_án>

# Khởi tạo môi trường ảo (Windows)
python -m venv venv
venv\Scripts\activate

```

**2. Cài đặt các thư viện phụ thuộc**

```bash
pip install -r requirements.txt

```

*(Đảm bảo máy tính của bạn đã thiết lập đúng biến môi trường PATH cho Windows để tránh lỗi mạng nội bộ).*

**3. Khởi chạy Backend Server**

```bash
uvicorn main:app --reload

```

**4. Kiểm thử API**

* Truy cập Swagger UI tại: `[http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)`
* Sử dụng endpoint `POST /api/v1/transactions/evaluate` với payload JSON mẫu để kiểm tra luồng tích hợp AI và txhash.

## 🛡️ Cam Kết Của Chúng Tôi

Chúng tôi tin rằng sự minh bạch là chìa khóa của mọi giao dịch. Hệ thống này không chỉ là một công cụ công nghệ, mà là **lời cam kết về giá trị thực** mà công ty chúng tôi mang lại cho thị trường xe ô tô cũ.
