from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.queries import (
    register_user,
    get_financial_overview,
    get_all_funds,
    delete_fund,
    get_fund_by_name,
    set_fund_balance
)
from utils.formatters import format_currency

router = Router()

def make_overview_keyboard() -> types.InlineKeyboardMarkup:
    """Tạo bàn phím inline cho tổng quan tài chính."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Làm mới", callback_data="refresh_overview")
    builder.adjust(1)
    return builder.as_markup()

def make_funds_list_keyboard(funds: list) -> types.InlineKeyboardMarkup:
    """Tạo bàn phím inline danh sách các quỹ để người dùng tương tác."""
    builder = InlineKeyboardBuilder()
    for fund in funds:
        builder.button(
            text=f"{fund['icon']} {fund['name']}: {format_currency(fund['balance'])}",
            callback_data=f"fund_info_{fund['id']}"
        )
    builder.button(text="🔄 Làm mới", callback_data="refresh_overview")
    builder.adjust(1)
    return builder.as_markup()

def render_overview_text(overview: dict) -> str:
    """Tạo nội dung hiển thị tổng quan tài chính."""
    current_balance = overview["current_balance"]
    is_initialized = overview["is_balance_initialized"]
    funds = overview["funds"]
    total_funds = overview["total_funds"]
    unallocated = overview["unallocated"]

    if not is_initialized:
        balance_str = "*(Chưa cài đặt - hãy nhắn: 'Set số dư 10 triệu')*"
    else:
        balance_str = f"**{format_currency(current_balance)}**"

    lines = [
        "💳 **TỔNG QUAN TÀI CHÍNH CÁ NHÂN**",
        "──────────────────",
        f"💰 **Số dư ví hiện tại:** {balance_str}",
    ]

    if funds:
        lines.append(f"\n📦 **Tổng tiền trong các quỹ:** **{format_currency(total_funds)}** ({len(funds)} quỹ)")
        for f in funds:
            lines.append(f"• {f['icon']} *{f['name']}:* **{format_currency(f['balance'])}**")

        if is_initialized:
            free_money_icon = "💵" if unallocated >= 0 else "⚠️"
            lines.append(f"\n{free_money_icon} **Tiền khả dụng (chưa vào quỹ):** **{format_currency(unallocated)}**")
    else:
        lines.append("\n📦 **Quỹ tài chính:** Bạn chưa có quỹ nào.")
        lines.append("💡 *Hãy thử nhắn:* `Tạo quỹ Du lịch 2 củ` hoặc `Lập quỹ Tiết kiệm 5tr`")

    lines.append("\n──────────────────")
    lines.append("💡 *Bạn có thể nhắn tự nhiên bất cứ lúc nào:*")
    lines.append("• `Set số dư 20 triệu`")
    lines.append("• `Tạo quỹ Đầu tư 5 củ`")
    lines.append("• `Set quỹ Du lịch 3tr`")

    return "\n".join(lines)

@router.message(Command("sodu"))
async def cmd_sodu(message: types.Message):
    """Lệnh /sodu - Xem số dư ví và tổng quan tài chính."""
    user_id = message.from_user.id
    await register_user(user_id, message.from_user.username)
    overview = await get_financial_overview(user_id)
    text = render_overview_text(overview)
    await message.answer(text, reply_markup=make_overview_keyboard(), parse_mode="Markdown")

@router.message(Command("quy"))
async def cmd_quy(message: types.Message):
    """Lệnh /quy - Xem danh sách các quỹ tài chính."""
    user_id = message.from_user.id
    await register_user(user_id, message.from_user.username)
    overview = await get_financial_overview(user_id)
    funds = overview["funds"]

    if not funds:
        await message.answer(
            "📦 **BẠN CHƯA CÓ QUỸ TÀI CHÍNH NÀO**\n\n"
            "💡 Bạn có thể tạo quỹ cực nhanh bằng cách nhắn:\n"
            "• `Tạo quỹ Tiết kiệm 5 triệu`\n"
            "• `Lập quỹ Du lịch với 2 củ`\n"
            "• `Tạo quỹ Khẩn cấp`",
            parse_mode="Markdown"
        )
        return

    text = render_overview_text(overview)
    await message.answer(text, reply_markup=make_funds_list_keyboard(funds), parse_mode="Markdown")

@router.callback_query(F.data == "refresh_overview")
async def callback_refresh_overview(call: types.CallbackQuery):
    """Làm mới thông tin tổng quan."""
    user_id = call.from_user.id
    overview = await get_financial_overview(user_id)
    text = render_overview_text(overview)
    try:
        await call.message.edit_text(text, reply_markup=make_overview_keyboard(), parse_mode="Markdown")
    except Exception:
        pass
    await call.answer("Đã cập nhật dữ liệu mới nhất!")

@router.callback_query(F.data.startswith("fund_info_"))
async def callback_fund_info(call: types.CallbackQuery):
    """Xem thông tin chi tiết một quỹ khi bấm vào nút."""
    fund_id = int(call.data.split("_")[2])
    user_id = call.from_user.id
    funds = await get_all_funds(user_id)
    fund = next((f for f in funds if f["id"] == fund_id), None)

    if not fund:
        await call.answer("Quỹ này không tồn tại hoặc đã bị xóa!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🗑️ Xóa quỹ này", callback_data=f"del_fund_{fund['name']}")
    builder.button(text="🔙 Danh sách quỹ", callback_data="refresh_overview")
    builder.adjust(2)

    msg = (
        f"{fund['icon']} **QUỸ: {fund['name']}**\n"
        f"──────────────────\n"
        f"💰 **Số dư hiện tại:** **{format_currency(fund['balance'])}**\n\n"
        f"💡 Để thay đổi số tiền quỹ này, bạn chỉ cần nhắn:\n"
        f"• `Set quỹ {fund['name']} <số tiền>` (vd: `Set quỹ {fund['name']} 5 củ`)"
    )
    await call.message.edit_text(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data.startswith("del_fund_"))
async def callback_delete_fund(call: types.CallbackQuery):
    """Xóa quỹ."""
    fund_name = call.data.replace("del_fund_", "")
    user_id = call.from_user.id
    success = await delete_fund(user_id, fund_name)

    if success:
        await call.answer(f"Đã xóa quỹ '{fund_name}'!", show_alert=True)
    else:
        await call.answer("Không thể xóa quỹ!", show_alert=True)

    overview = await get_financial_overview(user_id)
    text = render_overview_text(overview)
    await call.message.edit_text(text, reply_markup=make_overview_keyboard(), parse_mode="Markdown")
