from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.queries import (
    register_user,
    add_transaction,
    delete_transaction,
    update_transaction_category,
    get_daily_expense,
    get_budget_status,
    get_transaction,
    get_user_balance,
    set_user_balance,
    create_fund,
    set_fund_balance,
    delete_fund,
    get_financial_overview
)
from services.groq_service import groq_service
from utils.formatters import format_currency, get_category_icon, CATEGORY_ICONS
from handlers.fund import render_overview_text, make_overview_keyboard, make_funds_list_keyboard

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
async def handle_natural_language(message: types.Message):
    """Xử lý mọi tin nhắn ngôn ngữ tự nhiên: Thu chi, Số dư, Quỹ, Trò chuyện."""
    user_id = message.from_user.id
    await register_user(user_id, message.from_user.username)

    parsed = await groq_service.parse_financial_message(message.text)

    # 1. INTENT: Cài đặt số dư hiện tại (Set balance)
    if parsed.intent == "set_balance":
        if parsed.balance_amount is None:
            await message.answer(
                "🤔 Bạn muốn cài đặt số dư là bao nhiêu?\n"
                "💡 *Ví dụ bạn có thể nhắn:*\n"
                "• `Set số dư hiện tại của tôi là 15 triệu`\n"
                "• `Số dư ví là 5 củ`\n"
                "• `Hiện tại tài khoản có 20tr`",
                parse_mode="Markdown"
            )
            return

        new_bal = await set_user_balance(user_id, parsed.balance_amount)
        overview = await get_financial_overview(user_id)

        msg = (
            "💳 **ĐÃ CẬP NHẬT SỐ DƯ HIỆN TẠI**\n"
            "──────────────────\n"
            f"💰 **Số dư mới:** **{format_currency(new_bal)}**\n"
            f"📦 **Tổng tiền trong các quỹ:** **{format_currency(overview['total_funds'])}**\n"
            f"💵 **Tiền khả dụng (chưa vào quỹ):** **{format_currency(overview['unallocated'])}**\n\n"
            "✨ *Từ bây giờ, mọi khoản thu/chi phát sinh sẽ tự động được cộng/trừ vào số dư này!*"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="📊 Xem tổng quan", callback_data="refresh_overview")
        await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
        return

    # 2. INTENT: Xem số dư & tổng quan (Get balance)
    if parsed.intent == "get_balance":
        overview = await get_financial_overview(user_id)
        text = render_overview_text(overview)
        await message.answer(text, reply_markup=make_overview_keyboard(), parse_mode="Markdown")
        return

    # 3. INTENT: Tạo quỹ mới (Create fund)
    if parsed.intent == "create_fund":
        fund_name = parsed.fund_name
        if not fund_name:
            await message.answer(
                "🤔 Bạn muốn tạo quỹ tên gì?\n"
                "💡 *Ví dụ:*\n"
                "• `Tạo quỹ Du lịch 3 củ`\n"
                "• `Lập quỹ Tiết kiệm với 5 triệu`\n"
                "• `Tạo quỹ Mua xe máy`",
                parse_mode="Markdown"
            )
            return

        fund_amount = parsed.fund_amount or 0
        res = await create_fund(user_id, fund_name, initial_balance=fund_amount)

        if res["created"]:
            f = res["fund"]
            msg = (
                "🎉 **ĐÃ TẠO QUỸ MỚI THÀNH CÔNG!**\n"
                "──────────────────\n"
                f"{f['icon']} **Quỹ:** *{f['name']}*\n"
                f"💰 **Số dư ban đầu:** **{format_currency(f['balance'])}**\n\n"
                f"💡 *Bạn có thể thay đổi số tiền quỹ bất cứ lúc nào:*\n"
                f"• Nhắn: `Set quỹ {f['name']} 5 củ`"
            )
        else:
            existing = res["fund"]
            msg = (
                f"ℹ️ **Quỹ '{existing['name']}' đã tồn tại từ trước!**\n"
                f"──────────────────\n"
                f"{existing['icon']} **Số dư hiện tại:** **{format_currency(existing['balance'])}**\n\n"
                f"💡 Bạn muốn đổi số tiền quỹ này? Chỉ cần nhắn:\n"
                f"• `Set quỹ {existing['name']} <số tiền>`"
            )

        builder = InlineKeyboardBuilder()
        builder.button(text="📦 Danh sách các quỹ", callback_data="refresh_overview")
        await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
        return

    # 4. INTENT: Đặt số dư cho quỹ (Set fund balance)
    if parsed.intent == "set_fund_balance":
        fund_name = parsed.fund_name
        fund_amount = parsed.fund_amount

        if not fund_name or fund_amount is None:
            await message.answer(
                "🤔 Bạn muốn đặt số tiền bao nhiêu cho quỹ nào?\n"
                "💡 *Ví dụ:*\n"
                "• `Set quỹ Tiết kiệm 5 triệu`\n"
                "• `Đặt quỹ Du lịch thành 3 củ rưỡi`\n"
                "• `Quỹ Mua xe có 15tr`",
                parse_mode="Markdown"
            )
            return

        fund = await set_fund_balance(user_id, fund_name, fund_amount)

        if fund:
            prev_str = format_currency(fund["previous_balance"])
            new_str = format_currency(fund["balance"])
            msg = (
                f"✅ **ĐÃ CẬP NHẬT QUỸ [{fund['name']}]**\n"
                "──────────────────\n"
                f"{fund['icon']} **Số dư mới:** **{new_str}**\n"
                f"📊 *(Số dư trước đó: {prev_str})*"
            )
        else:
            # Tự động tạo quỹ mới nếu chưa có
            res = await create_fund(user_id, fund_name, initial_balance=fund_amount)
            f = res["fund"]
            msg = (
                f"✨ Quỹ *{fund_name}* chưa có, tôi đã tự động tạo mới giúp bạn:\n"
                "──────────────────\n"
                f"{f['icon']} **Quỹ:** *{f['name']}*\n"
                f"💰 **Số dư:** **{format_currency(f['balance'])}**"
            )

        builder = InlineKeyboardBuilder()
        builder.button(text="📦 Xem các quỹ", callback_data="refresh_overview")
        await message.answer(msg, reply_markup=builder.as_markup(), parse_mode="Markdown")
        return

    # 5. INTENT: Xem danh sách các quỹ (Get funds)
    if parsed.intent == "get_funds":
        overview = await get_financial_overview(user_id)
        funds = overview["funds"]
        if not funds:
            await message.answer(
                "📦 **BẠN CHƯA CÓ QUỸ NÀO**\n\n"
                "💡 Bạn có thể tạo quỹ cực nhanh bằng cách nhắn:\n"
                "• `Tạo quỹ Du lịch 2 củ`\n"
                "• `Lập quỹ Tiết kiệm 5 triệu`",
                parse_mode="Markdown"
            )
            return
        text = render_overview_text(overview)
        await message.answer(text, reply_markup=make_funds_list_keyboard(funds), parse_mode="Markdown")
        return

    # 6. INTENT: Xóa quỹ (Delete fund)
    if parsed.intent == "delete_fund":
        fund_name = parsed.fund_name
        if not fund_name:
            await message.answer("🤔 Bạn muốn xóa quỹ nào? (Ví dụ: `Xóa quỹ Du lịch`)")
            return

        success = await delete_fund(user_id, fund_name)
        if success:
            await message.answer(f"🗑️ Đã xóa thành công quỹ *{fund_name}*!", parse_mode="Markdown")
        else:
            await message.answer(f"Không tìm thấy quỹ *{fund_name}* để xóa.", parse_mode="Markdown")
        return

    # 7. INTENT: Ghi nhận thu/chi (Record transaction)
    if parsed.intent == "record_transaction" and parsed.items:
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
            user_bal = await get_user_balance(user_id)

            balance_line = ""
            if user_bal["is_initialized"]:
                balance_line = f"\n💳 *Số dư ví còn lại:* **{format_currency(user_bal['current_balance'])}**"

            reply_text = (
                f"✅ **Đã ghi nhận {type_str}:**\n"
                f"{icon} *{item.note.capitalize()}:* **{sign}{format_currency(item.amount)}** `[{item.category}]`\n"
                f"──────────────────\n"
                f"💰 *Tổng chi hôm nay:* **{format_currency(daily_total)}**"
                f"{balance_line}"
                f"{warning_msg}"
            )

            await message.answer(
                reply_text,
                reply_markup=make_transaction_keyboard(trans_id),
                parse_mode="Markdown"
            )
        return

    # 8. INTENT: Trò chuyện hoặc không nhận diện được
    if parsed.reply_message:
        await message.answer(parsed.reply_message, parse_mode="Markdown")
        return

    # Fallback hướng dẫn
    await message.answer(
        "🤔 Tôi chưa hiểu rõ ý định của bạn.\n\n"
        "💡 *Bạn có thể nhắn tự nhiên như:* \n"
        "• `Ăn sáng phở bò 45k` (ghi chép chi tiêu)\n"
        "• `Set số dư hiện tại của tôi là 10 triệu` (cài số dư)\n"
        "• `Tạo quỹ Du lịch 3 củ` (lập quỹ)\n"
        "• `Set quỹ Du lịch 5 triệu` (đặt tiền quỹ)\n"
        "• `Số dư của tôi còn bao nhiêu?` (xem ví)",
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
        user_bal = await get_user_balance(user_id)
        bal_line = ""
        if user_bal["is_initialized"]:
            bal_line = f"\n💳 *Số dư ví đã hoàn lại thành:* **{format_currency(user_bal['current_balance'])}**"

        await call.message.edit_text(
            f"❌ **Đã hủy bỏ giao dịch này.**\n"
            f"💰 *Tổng chi hôm nay cập nhật lại:* **{format_currency(daily_total)}**"
            f"{bal_line}",
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
