from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.queries import get_all_active_user_ids, get_daily_expense
from utils.formatters import format_currency
from config.settings import settings

async def send_daily_reminder(bot: Bot) -> None:
    """Gửi tin nhắn nhắc nhở và tổng kết ngày cho toàn bộ người dùng active."""
    user_ids = await get_all_active_user_ids()

    for user_id in user_ids:
        try:
            today_spent = await get_daily_expense(user_id)
            spent_str = format_currency(today_spent)

            msg = (
                "🌙 **TỔNG KẾT NGÀY HÔM NAY**\n\n"
                f"💰 Tổng chi tiêu hôm nay của bạn: **{spent_str}**.\n\n"
                "❓ Có khoản chi tiêu hoặc thu nhập nào hôm nay bạn quên chưa ghi không?\n"
                "👉 Hãy nhắn ngay cho tôi (ví dụ: *'Ăn vặt 30k'*) để sổ thu chi luôn chuẩn xác nhé!"
            )
            await bot.send_message(user_id, msg, parse_mode="Markdown")
        except Exception:
            # Bỏ qua nếu user đã block bot hoặc gặp lỗi mạng
            continue

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Khởi tạo và cấu hình cron job chạy hàng ngày."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_daily_reminder,
        trigger="cron",
        hour=settings.reminder_hour,
        minute=settings.reminder_minute,
        args=[bot]
    )
    return scheduler
