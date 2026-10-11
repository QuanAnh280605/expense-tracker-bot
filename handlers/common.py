from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from database.queries import register_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Xử lý lệnh /start."""
    user = message.from_user
    await register_user(user.id, user.username)

    welcome_text = (
        f"👋 Xin chào **{user.full_name}**!\n\n"
        "🤖 Tôi là **Bot Quản Lý Thu Chi Thông Minh**, hỗ trợ bạn ghi chép tài chính cá nhân siêu tốc với AI Groq.\n\n"
        "💡 **Cách sử dụng cực kỳ đơn giản:**\n"
        "Chỉ cần nhắn tin tự nhiên như nói chuyện bình thường:\n"
        "• *'Ăn sáng phở bò 45k'*\n"
        "• *'Đổ xăng 70k, mua ly cafe 25k'*\n"
        "• *'Vừa nhận lương 15 củ'*\n"
        "• *'Mua áo sơ mi 2 lít rưỡi'*\n\n"
        "📊 **Các lệnh quản lý:**\n"
        "/baocao - Xem báo cáo & biểu đồ thu chi\n"
        "/ngansach - Cài đặt & theo dõi hạn mức chi tiêu\n"
        "/export - Xuất toàn bộ dữ liệu ra file Excel (.xlsx)\n"
        "/help - Hướng dẫn chi tiết"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Xử lý lệnh /help."""
    help_text = (
        "📖 **HƯỚNG DẪN SỬ DỤNG CHI TIẾT**\n\n"
        "1️⃣ **Ghi chép thu chi:**\n"
        "Bạn có thể nhắn tin bằng tiếng Việt có dấu hoặc không dấu, bot hiểu được các từ lóng:\n"
        "• `k`, `nghìn` -> 1.000đ (vd: 50k)\n"
        "• `lít`, `xị` -> 100.000đ (vd: 2 lít = 200.000đ)\n"
        "• `củ`, `chai`, `tr` -> 1.000.000đ (vd: 1 củ 2 = 1.200.000đ)\n\n"
        "2️⃣ **Sửa / Hủy giao dịch:**\n"
        "Sau mỗi lần ghi nhận, bot sẽ gửi kèm nút **[❌ Hủy]** và **[✏️ Đổi danh mục]** ngay dưới tin nhắn để bạn sửa lại 1 chạm.\n\n"
        "3️⃣ **Xem báo cáo:**\n"
        "• Gõ `/baocao` để xem thống kê theo ngày/tuần/tháng kèm biểu đồ tròn.\n\n"
        "4️⃣ **Cài đặt ngân sách:**\n"
        "• Gõ `/ngansach Ăn uống 3000000` để đặt giới hạn 3 triệu cho tiền ăn.\n\n"
        "5️⃣ **Xuất file Excel:**\n"
        "• Gõ `/export` để tải file bảng tính .xlsx về máy tính/điện thoại."
    )
    await message.answer(help_text, parse_mode="Markdown")
