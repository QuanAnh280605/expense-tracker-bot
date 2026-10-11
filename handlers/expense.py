from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.queries import (
    register_user,
    add_transaction,
    delete_transaction,
    update_transaction_category,
    get_daily_expense,
    get_budget_status,
    get_transaction
)
from services.groq_service import groq_service
from utils.formatters import format_currency, get_category_icon, CATEGORY_ICONS

router = Router()

def make_transaction_keyboard(transaction_id: int) -> types.InlineKeyboardMarkup:
    """Tạo inline keyboard cho một giao dịch vừa thêm."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Hủy", callback_data=f"cancel_{transaction_id}")
    builder.button(text="✏️ Đổi danh mục", callback_data=f"catmenu_{transaction_id}")
    builder.adjust(2)
    return builder.as_markup()

def make_category_select_keyboard(transaction_id: int) -> types.InlineKeyboardMarkup:
    """Tạo menu các danh mục để người dùng bấm chọn đổi."""
    builder = InlineKeyboardBuilder()
    for cat, icon in CATEGORY_ICONS.items():
        builder.button(text=f"{icon} {cat}", callback_data=f"setcat_{transaction_id}_{cat}")
    builder.button(text="🔙 Quay lại", callback_data=f"back_{transaction_id}")
    builder.adjust(3)
    return builder.as_markup()

@router.message(F.text & ~F.text.startswith("/"))
async def handle_expense_text(message: types.Message):
    """Xử lý tin nhắn văn bản thông thường để trích xuất khoản thu chi."""
    user_id = message.from_user.id
    await register_user(user_id, message.from_user.username)

    parsed = await groq_service.parse_expense_text(message.text)

    if not parsed.is_financial or not parsed.items:
        await message.answer(
            "🤔 Tôi chưa nhận diện được khoản thu chi nào trong tin nhắn này.\n\n"
            "💡 *Ví dụ bạn có thể nhắn:*\n"
            "• `Ăn sáng bún bò 45k`\n"
            "• `Đổ xăng 70k, cafe 25k`\n"
            "• `Nhận lương 15 củ`",
            parse_mode="Markdown"
        )
        return

    # Lưu từng item vào database
    for item in parsed.items:
        trans_id = await add_transaction(
            user_id=user_id,
            amount=item.amount,
            trans_type=item.type,
            category=item.category,
            note=item.note
        )

        icon = get_category_icon(item.category)
        type_str = "Thu nhập" if item.type == "income" else "Chi tiêu"
        sign = "+" if item.type == "income" else "-"

        # Kiểm tra cảnh báo ngân sách nếu là khoản chi
        warning_msg = ""
        if item.type == "expense":
            b_status = await get_budget_status(user_id, item.category)
            if b_status:
                if b_status["percent"] >= 100:
                    warning_msg = (
                        f"\n\n🚨 **CẢNH BÁO:** Bạn đã vượt hạn mức danh mục *{item.category}* "
                        f"({format_currency(b_status['spent'])} / {format_currency(b_status['monthly_limit'])})!"
                    )
                elif b_status["percent"] >= 80:
                    warning_msg = (
                        f"\n\n⚠️ **LƯU Ý:** Đã tiêu {b_status['percent']:.0f}% hạn mức *{item.category}* "
                        f"({format_currency(b_status['spent'])} / {format_currency(b_status['monthly_limit'])})."
                    )

        daily_total = await get_daily_expense(user_id)

        reply_text = (
            f"✅ **Đã ghi nhận {type_str}:**\n"
            f"{icon} *{item.note.capitalize()}:* **{sign}{format_currency(item.amount)}** `[{item.category}]`\n"
            f"──────────────────\n"
            f"💰 *Tổng chi hôm nay:* **{format_currency(daily_total)}**"
            f"{warning_msg}"
        )

        await message.answer(
            reply_text,
            reply_markup=make_transaction_keyboard(trans_id),
            parse_mode="Markdown"
        )

@router.callback_query(F.data.startswith("cancel_"))
async def callback_cancel_transaction(call: types.CallbackQuery):
    """Xử lý khi người dùng bấm Hủy giao dịch."""
    trans_id = int(call.data.split("_")[1])
    user_id = call.from_user.id

    success = await delete_transaction(trans_id, user_id)
    if success:
        daily_total = await get_daily_expense(user_id)
        await call.message.edit_text(
            f"❌ **Đã hủy bỏ giao dịch này.**\n"
            f"💰 *Tổng chi hôm nay cập nhật lại:* **{format_currency(daily_total)}**",
            parse_mode="Markdown"
        )
    else:
        await call.answer("Giao dịch không tồn tại hoặc đã bị xóa trước đó.", show_alert=True)

@router.callback_query(F.data.startswith("catmenu_"))
async def callback_category_menu(call: types.CallbackQuery):
    """Mở menu chọn danh mục mới."""
    trans_id = int(call.data.split("_")[1])
    await call.message.edit_reply_markup(
        reply_markup=make_category_select_keyboard(trans_id)
    )

@router.callback_query(F.data.startswith("setcat_"))
async def callback_set_category(call: types.CallbackQuery):
    """Cập nhật danh mục mới cho giao dịch."""
    parts = call.data.split("_")
    trans_id = int(parts[1])
    new_cat = parts[2]
    user_id = call.from_user.id

    success = await update_transaction_category(trans_id, user_id, new_cat)
    if success:
        trans = await get_transaction(trans_id, user_id)
        daily_total = await get_daily_expense(user_id)
        icon = get_category_icon(new_cat)
        amount_str = format_currency(trans["amount"]) if trans else ""
        note = trans["note"] if trans else ""

        await call.message.edit_text(
            f"✅ **Đã cập nhật danh mục thành:** {icon} *{new_cat}*\n"
            f"📌 *{note}:* **-{amount_str}**\n"
            f"──────────────────\n"
            f"💰 *Tổng chi hôm nay:* **{format_currency(daily_total)}**",
            reply_markup=make_transaction_keyboard(trans_id),
            parse_mode="Markdown"
        )
    else:
        await call.answer("Không tìm thấy giao dịch để sửa.", show_alert=True)

@router.callback_query(F.data.startswith("back_"))
async def callback_back(call: types.CallbackQuery):
    """Quay lại giao diện nút ban đầu."""
    trans_id = int(call.data.split("_")[1])
    await call.message.edit_reply_markup(
        reply_markup=make_transaction_keyboard(trans_id)
    )
