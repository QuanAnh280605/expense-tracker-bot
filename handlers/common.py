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
        "🤖 Tôi là **Bot Quản Lý Thu Chi Thông Minh**, hỗ trợ bạn quản lý tài chính cá nhân siêu tốc với AI Groq.\n\n"
        "💡 **Bạn KHÔNG cần gõ command phức tạp, chỉ cần nhắn tin tự nhiên:**\n"
        "• *'Set số dư hiện tại của tôi là 15 triệu'* ➔ Cài số dư ví\n"
        "• *'Tạo quỹ Du lịch 3 củ'* ➔ Tạo quỹ tài chính\n"
        "• *'Set quỹ Tiết kiệm 5 triệu'* ➔ Điều chỉnh số tiền trong quỹ\n"
        "• *'Ăn sáng phở bò 45k'* ➔ Tự ghi chép & trừ vào số dư\n"
        "• *'Đổ xăng 70k, mua cafe 25k'* ➔ Ghi nhiều khoản 1 lúc\n"
        "• *'Vừa nhận lương 20 củ'* ➔ Ghi thu nhập & cộng vào số dư\n"
        "• *'Số dư của tôi còn bao nhiêu?'* ➔ Xem ví & các quỹ\n\n"
        "📊 **Các lệnh hỗ trợ nhanh:**\n"
        "/sodu - Xem số dư ví & tổng quan tài chính\n"
        "/quy - Xem & quản lý danh sách các quỹ\n"
        "/baocao - Xem báo cáo & biểu đồ thu chi\n"
        "/ngansach - Cài đặt & theo dõi hạn mức chi tiêu\n"
        "/export - Xuất toàn bộ dữ liệu ra file Excel (.xlsx)\n"
        "/help - Xem hướng dẫn chi tiết"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Xử lý lệnh /help."""
    help_text = (
        "📖 **HƯỚNG DẪN SỬ DỤNG CHI TIẾT**\n\n"
        "1️⃣ **Cài đặt & Theo dõi số dư (Tự động):**\n"
        "Chỉ cần nhắn cho bot:\n"
        "• `Set số dư hiện tại của tôi là 20 triệu` (hoặc `Ví tôi có 15 củ`)\n"
        "• `Số dư của tôi còn bao nhiêu?` (hoặc gõ `/sodu`)\n"
        "Mỗi khi bạn ghi nhận chi tiêu/thu nhập, số dư sẽ tự động được cộng/trừ theo thời gian thực!\n\n"
        "2️⃣ **Quản lý Quỹ tài chính (Tự động):**\n"
        "Tạo và phân bổ tiền vào các hũ/quỹ tự do không cần gõ lệnh:\n"
        "• `Tạo quỹ Du lịch 3 củ` hoặc `Lập quỹ Tiết kiệm`\n"
        "• `Set quỹ Tiết kiệm 5 triệu` hoặc `Đặt quỹ Du lịch thành 2tr`\n"
        "• `Xem các quỹ` (hoặc gõ `/quy`)\n"
        "• `Xóa quỹ Du lịch`\n\n"
        "3️⃣ **Ghi chép thu chi hàng ngày:**\n"
        "Hỗ trợ đầy đủ tiếng lóng & từ viết tắt:\n"
        "• `k`, `nghìn` ➔ 1.000đ (vd: 50k)\n"
        "• `lít`, `xị` ➔ 100.000đ (vd: 2 lít = 200.000đ)\n"
        "• `củ`, `chai`, `tr` ➔ 1.000.000đ (vd: 1 củ 2 = 1.200.000đ)\n\n"
        "4️⃣ **Sửa / Hủy giao dịch:**\n"
        "Sau mỗi lần ghi nhận, có nút **[❌ Hủy]** (tự động hoàn tiền vào số dư) và **[✏️ Đổi danh mục]** 1 chạm.\n\n"
        "5️⃣ **Báo cáo & Ngân sách:**\n"
        "• `/baocao` - Xem thống kê ngày/tuần/tháng kèm biểu đồ tròn.\n"
        "• `/ngansach Ăn uống 3000000` - Đặt hạn mức chi tiêu tháng.\n"
        "• `/export` - Tải file Excel .xlsx."
    )
    await message.answer(help_text, parse_mode="Markdown")
