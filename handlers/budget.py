import re
from datetime import date
from aiogram import Router, types
from aiogram.filters import Command
from database.queries import set_budget, get_budget_status
from utils.formatters import format_currency, get_category_icon, CATEGORY_ICONS

router = Router()

def parse_budget_amount(amount_str: str) -> int:
    """Chuyển đổi chuỗi số tiền ngân sách thành số nguyên."""
    text = amount_str.lower().strip().replace(".", "").replace(",", "")

    # Xử lý các từ viết tắt
    if "củ" in text or "tr" in text or "triệu" in text or "m" in text:
        num = re.findall(r"[\d.]+", text)
        if num:
            return int(float(num[0]) * 1_000_000)
    elif "lít" in text or "xị" in text:
        num = re.findall(r"[\d.]+", text)
        if num:
            return int(float(num[0]) * 100_000)
    elif "k" in text or "nghìn" in text or "ngàn" in text:
        num = re.findall(r"[\d.]+", text)
        if num:
            return int(float(num[0]) * 1_000)

    # Nếu là số thuần túy
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0

def make_progress_bar(percent: float) -> str:
    """Tạo thanh tiến độ trực quan: [██████░░░░] 60%"""
    blocks = int(min(max(percent, 0), 100) / 10)
    bar = "█" * blocks + "░" * (10 - blocks)
    return f"`[{bar}]` {percent:.0f}%"

@router.message(Command("ngansach"))
async def cmd_budget(message: types.Message):
    """Quản lý và thiết lập ngân sách chi tiêu hàng tháng."""
    args = message.text.split(maxsplit=2)
    user_id = message.from_user.id

    # Trường hợp 1: Không có tham số -> Hiển thị danh sách ngân sách hiện tại
    if len(args) == 1:
        today = date.today()
        lines = [
            f"🎯 **NGÂN SÁCH THÁNG {today.month}/{today.year}**\n",
            "💡 *Để đặt hạn mức mới, gõ:*\n`/ngansach <Danh mục> <Số tiền>`\n*(Ví dụ: `/ngansach Ăn uống 3tr`)*\n",
            "──────────────────"
        ]

        has_budget = False
        for cat in CATEGORY_ICONS.keys():
            if cat in ("Lương thưởng", "Khác"):
                continue
            b = await get_budget_status(user_id, cat)
            if b:
                has_budget = True
                icon = get_category_icon(cat)
                progress = make_progress_bar(b["percent"])
                status_icon = "🚨" if b["percent"] >= 100 else ("⚠️" if b["percent"] >= 80 else "✅")

                lines.append(
                    f"{status_icon} {icon} **{cat}:** {format_currency(b['spent'])} / {format_currency(b['monthly_limit'])}\n"
                    f"   {progress}\n"
                )

        if not has_budget:
            lines.append("*(Bạn chưa cài đặt ngân sách nào. Hãy đặt thử một danh mục nhé!)*")

        await message.answer("\n".join(lines), parse_mode="Markdown")
        return

    # Trường hợp 2: Cài đặt ngân sách mới -> /ngansach <category> <amount>
    if len(args) >= 3:
        input_cat = args[1].replace("_", " ").strip()
        input_amount = args[2].strip()

        # Tìm danh mục khớp nhất
        matched_cat = None
        for cat in CATEGORY_ICONS.keys():
            if input_cat.lower() in cat.lower():
                matched_cat = cat
                break

        if not matched_cat:
            avail_cats = ", ".join(list(CATEGORY_ICONS.keys()))
            await message.answer(
                f"⚠️ Không nhận diện được danh mục *'{input_cat}'*.\n"
                f"Các danh mục hợp lệ: {avail_cats}",
                parse_mode="Markdown"
            )
            return

        amount = parse_budget_amount(input_amount)
        if amount <= 0:
            await message.answer("⚠️ Số tiền ngân sách không hợp lệ. Vui lòng nhập số tiền lớn hơn 0.")
            return

        await set_budget(user_id, matched_cat, amount)
        icon = get_category_icon(matched_cat)
        await message.answer(
            f"🎯 **Đã cài đặt ngân sách thành công!**\n\n"
            f"{icon} Danh mục: **{matched_cat}**\n"
            f"💰 Hạn mức: **{format_currency(amount)}/tháng**\n\n"
            f"Bot sẽ tự động cảnh báo khi bạn chi tiêu chạm mốc 80% hoặc 100%.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "⚠️ Sai cú pháp! Vui lòng gõ theo mẫu:\n`/ngansach <Tên danh mục> <Số tiền>`\n\n"
            "Ví dụ:\n• `/ngansach Ăn uống 3000000`\n• `/ngansach Đi lại 500k`",
            parse_mode="Markdown"
        )
