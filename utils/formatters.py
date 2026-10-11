from datetime import datetime

CATEGORY_ICONS = {
    "Ăn uống": "🍜",
    "Đi lại": "🚗",
    "Mua sắm": "🛍️",
    "Nhà cửa": "🏠",
    "Giải trí": "🎮",
    "Sức khỏe": "💊",
    "Hóa đơn": "🧾",
    "Lương thưởng": "💰",
    "Khác": "📦",
}

def get_category_icon(category: str) -> str:
    """Trả về icon tương ứng với danh mục."""
    return CATEGORY_ICONS.get(category, "📌")

def format_currency(amount: int) -> str:
    """Định dạng số tiền sang chuẩn Việt Nam (vd: 120.000đ)."""
    return f"{amount:,.0f}đ".replace(",", ".")

def format_datetime_vn(dt_str: str) -> str:
    """Chuyển đổi chuỗi timestamp ISO/SQLite sang định dạng ngày giờ VN."""
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_str
