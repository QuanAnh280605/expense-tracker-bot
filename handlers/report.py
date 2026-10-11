from datetime import date, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile

from database.queries import get_period_summary, get_all_transactions
from services.chart_service import generate_pie_chart
from services.excel_service import export_transactions_to_excel
from utils.formatters import format_currency, get_category_icon

router = Router()

def make_period_keyboard() -> types.InlineKeyboardMarkup:
    """Tạo inline keyboard chọn mốc thời gian báo cáo."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Hôm nay", callback_data="report_today")
    builder.button(text="🗓️ Tuần này", callback_data="report_week")
    builder.button(text="📆 Tháng này", callback_data="report_month")
    builder.adjust(3)
    return builder.as_markup()

async def generate_report_content(user_id: int, period: str):
    """Tính toán dữ liệu báo cáo theo mốc thời gian."""
    today = date.today()
    if period == "today":
        start_date = today.strftime("%Y-%m-%d")
        end_date = start_date
        title = f"Hôm nay ({today.strftime('%d/%m/%Y')})"
    elif period == "week":
        start_date = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        title = "Tuần này"
    else: # month
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        title = f"Tháng {today.month}/{today.year}"

    data = await get_period_summary(user_id, start_date, end_date)
    return title, data

@router.message(Command("baocao", "thongke"))
async def cmd_report(message: types.Message):
    """Xử lý lệnh /baocao."""
    await message.answer(
        "📊 **Chọn mốc thời gian bạn muốn xem báo cáo:**",
        reply_markup=make_period_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("report_"))
async def callback_report_period(call: types.CallbackQuery):
    """Xử lý hiển thị báo cáo theo mốc thời gian."""
    period = call.data.replace("report_", "")
    user_id = call.from_user.id

    title, data = await generate_report_content(user_id, period)

    total_expense = data["total_expense"]
    total_income = data["total_income"]
    net = data["net"]
    categories = data["categories"]

    lines = [
        f"📊 **BÁO CÁO THU CHI — {title.upper()}**\n",
        f"🔻 **Tổng chi:** `{format_currency(total_expense)}`",
        f"🔺 **Tổng thu:** `{format_currency(total_income)}`",
        f"⚖️ **Số dư:** `{format_currency(net)}`\n",
        "──────────────────",
        "📂 **Phân bổ chi tiêu:**"
    ]

    if not categories or total_expense == 0:
        lines.append("*(Chưa có khoản chi nào trong thời gian này)*")
    else:
        for cat, amount in categories.items():
            icon = get_category_icon(cat)
            pct = (amount / total_expense) * 100 if total_expense > 0 else 0
            lines.append(f"{icon} *{cat}:* {format_currency(amount)} (`{pct:.1f}%`)")

    report_text = "\n".join(lines)

    # Nếu có dữ liệu chi tiêu, vẽ biểu đồ tròn gửi kèm
    if categories and total_expense > 0:
        try:
            chart_buf = generate_pie_chart(categories, title=f"Phân Bổ Chi Tiêu - {title}")
            photo = BufferedInputFile(chart_buf.getvalue(), filename="chart.png")
            await call.message.delete()
            await call.message.answer_photo(
                photo=photo,
                caption=report_text,
                reply_markup=make_period_keyboard(),
                parse_mode="Markdown"
            )
            return
        except Exception:
            pass

    # Nếu không vẽ được chart hoặc không có chi tiêu, cập nhật text thông thường
    await call.message.edit_text(
        report_text,
        reply_markup=make_period_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("export"))
async def cmd_export(message: types.Message):
    """Xuất file Excel lịch sử thu chi."""
    user_id = message.from_user.id
    status_msg = await message.answer("⏳ Đang tổng hợp và tạo file Excel...")

    transactions = await get_all_transactions(user_id)
    if not transactions:
        await status_msg.edit_text("⚠️ Bạn chưa có dữ liệu giao dịch nào để xuất.")
        return

    excel_buf = export_transactions_to_excel(transactions)
    doc = BufferedInputFile(excel_buf.getvalue(), filename=f"lich_su_thu_chi_{date.today().strftime('%Y%m%d')}.xlsx")

    await status_msg.delete()
    await message.answer_document(
        document=doc,
        caption="📁 **Đây là toàn bộ lịch sử thu chi của bạn.**\nBạn có thể mở bằng Microsoft Excel hoặc Google Sheets.",
        parse_mode="Markdown"
    )
