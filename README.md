# 💰 Bot Telegram Quản Lý Thu Chi Thông Minh (Groq AI + SQLite)

Bot Telegram quản lý tài chính cá nhân siêu tốc, hỗ trợ nhập liệu bằng ngôn ngữ tự nhiên tiếng Việt qua **Groq AI (Llama 3.3 70B)**, tự động phân loại, vẽ biểu đồ tròn trực quan, cảnh báo ngân sách và xuất file Excel.

---

## ✨ Tính Năng Nổi Bật

1. **Ghi chép tự nhiên:** Nhắn tin tự nhiên như người thật, hiểu từ lóng và cách viết tắt tiếng Việt (`45k`, `2 lít`, `1 củ rưỡi`, `5 chục`,...).
2. **Hỗ trợ đa giao dịch:** Tách nhiều khoản chi trong cùng một tin nhắn (ví dụ: *"ăn trưa 40k, cafe 25k"*).
3. **Thao tác 1 chạm (Inline Keyboard):** Sau khi lưu, luôn có nút `[❌ Hủy]` và `[✏️ Đổi danh mục]` để chỉnh sửa tức thì nếu AI đoán nhầm.
4. **Báo cáo & Vẽ biểu đồ tự động:** Lệnh `/baocao` gửi ảnh biểu đồ tròn (Pie/Donut chart) phân bổ chi tiêu theo ngày, tuần, tháng.
5. **Cảnh báo ngân sách:** Lệnh `/ngansach` cho phép đặt hạn mức từng danh mục, tự động cảnh báo khi chi tiêu đạt **80%** hoặc vượt **100%**.
6. **Xuất file Excel:** Lệnh `/export` gửi ngay file `.xlsx` đầy đủ lịch sử thu chi để xem trên Excel / Google Sheets.
7. **Nhắc nhở cuối ngày:** Tự động gửi tổng kết chi tiêu vào lúc **22:00 mỗi tối** để tránh quên sót.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Bot

### 1. Chuẩn bị Token & API Key
- **Telegram Bot Token:** Nhắn tin cho `@BotFather` trên Telegram, gõ `/newbot` để tạo bot và lấy Token.
- **Groq API Key:** Đăng ký miễn phí tại [Groq Cloud Console](https://console.groq.com) và tạo API Key.

### 2. Cài đặt môi trường
Khuyến khích sử dụng Python 3.10 trở lên:

```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo:
# Trên Windows:
venv\Scripts\activate
# Trên Linux/macOS:
source venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
```

### 3. Cấu hình file `.env`
Sao chép file `.env.example` thành `.env`:
```bash
cp .env.example .env
```
Mở `.env` và điền token của bạn:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuvWXyz
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxx
```

### 4. Khởi chạy Bot
```bash
python main.py
```

---

## 🐳 Chạy Bằng Docker (Tùy chọn)

```bash
# Build image
docker build -t expense-tracker-bot .

# Chạy container
docker run -d --name my-expense-bot --restart always \
  -v $(pwd)/expense_tracker.db:/app/expense_tracker.db \
  --env-file .env \
  expense-tracker-bot
```

---

## 📖 Danh Sách Lệnh & Giao Tiếp Ngôn Ngữ Tự Nhiên

### 💬 Thao Tác Bằng Chat Tự Nhiên (Không Cần Gõ Lệnh)
- **Cài đặt số dư:** `Set số dư hiện tại của tôi là 15 triệu`, `Ví tôi còn 5 củ`
- **Tạo quỹ mới:** `Tạo quỹ Du lịch 3 củ`, `Lập quỹ Tiết kiệm với 5 triệu`, `Mở quỹ Mua xe`
- **Set số tiền quỹ:** `Set quỹ Tiết kiệm 10 triệu`, `Đặt quỹ Du lịch thành 2tr`, `Quỹ Khẩn cấp có 5 củ`
- **Xem ví & quỹ:** `Số dư của tôi còn bao nhiêu?`, `Xem danh sách quỹ`, `Các quỹ hiện có`
- **Xóa quỹ:** `Xóa quỹ Du lịch`
- **Ghi chép thu chi:** `Ăn trưa 40k`, `Đổ xăng 70k, cafe 25k`, `Nhận lương 20 củ` *(tự động cộng/trừ vào số dư)*

### ⌨️ Lệnh Telegram Hỗ Trợ
- `/start` - Khởi động và xem lời chào hướng dẫn
- `/help` - Xem hướng dẫn chi tiết
- `/sodu` - Xem số dư ví hiện tại, tiền trong quỹ và tiền khả dụng
- `/quy` - Xem và quản lý danh sách các quỹ tài chính
- `/baocao` - Xem thống kê và biểu đồ tròn thu chi
- `/ngansach` - Xem hoặc cài đặt hạn mức chi tiêu tháng (vd: `/ngansach Ăn uống 3tr`)
- `/export` - Xuất file Excel lịch sử thu chi (.xlsx)

