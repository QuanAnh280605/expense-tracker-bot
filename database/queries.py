from datetime import date
from typing import List, Dict, Any, Optional
from database.db import get_connection

async def register_user(user_id: int, username: Optional[str] = None) -> None:
    """Lưu hoặc cập nhật thông tin user."""
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
        """, (user_id, username))
        await conn.commit()

async def add_transaction(
    user_id: int,
    amount: int,
    trans_type: str,
    category: str,
    note: Optional[str] = None
) -> int:
    """Thêm một giao dịch mới và trả về ID."""
    async with get_connection() as conn:
        cursor = await conn.execute("""
            INSERT INTO transactions (user_id, amount, type, category, note)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, amount, trans_type, category, note))
        trans_id = cursor.lastrowid

        # Tự động cập nhật số dư tổng nếu user đã cài đặt số dư
        delta = amount if trans_type == "income" else -amount
        await conn.execute("""
            UPDATE users
            SET current_balance = current_balance + ?
            WHERE user_id = ? AND is_balance_initialized = 1
        """, (delta, user_id))

        await conn.commit()
        return trans_id

async def delete_transaction(transaction_id: int, user_id: int) -> bool:
    """Xóa một giao dịch (dùng cho chức năng Hủy) và hoàn lại số dư."""
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT amount, type FROM transactions
            WHERE id = ? AND user_id = ?
        """, (transaction_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            amount = row["amount"]
            trans_type = row["type"]

        cursor = await conn.execute("""
            DELETE FROM transactions
            WHERE id = ? AND user_id = ?
        """, (transaction_id, user_id))

        if cursor.rowcount > 0:
            # Hoàn lại số dư nếu user đã cài đặt số dư
            reverse_delta = -amount if trans_type == "income" else amount
            await conn.execute("""
                UPDATE users
                SET current_balance = current_balance + ?
                WHERE user_id = ? AND is_balance_initialized = 1
            """, (reverse_delta, user_id))

        await conn.commit()
        return cursor.rowcount > 0


async def update_transaction_category(
    transaction_id: int,
    user_id: int,
    new_category: str
) -> bool:
    """Cập nhật danh mục cho một giao dịch."""
    async with get_connection() as conn:
        cursor = await conn.execute("""
            UPDATE transactions
            SET category = ?
            WHERE id = ? AND user_id = ?
        """, (new_category, transaction_id, user_id))
        await conn.commit()
        return cursor.rowcount > 0

async def get_transaction(transaction_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Lấy thông tin 1 giao dịch."""
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT id, user_id, amount, type, category, note, transaction_date
            FROM transactions
            WHERE id = ? AND user_id = ?
        """, (transaction_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_daily_expense(user_id: int, target_date: Optional[date] = None) -> int:
    """Tính tổng chi tiêu trong 1 ngày."""
    if target_date is None:
        target_date = date.today()
    date_str = target_date.strftime("%Y-%m-%d")

    async with get_connection() as conn:
        async with conn.execute("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM transactions
            WHERE user_id = ? 
              AND type = 'expense'
              AND date(transaction_date) = date(?)
        """, (user_id, date_str)) as cursor:
            row = await cursor.fetchone()
            return row["total"] if row else 0

async def get_period_summary(
    user_id: int,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    Lấy báo cáo tổng hợp: Tổng thu, tổng chi và phân bổ theo danh mục chi tiêu.
    start_date, end_date dạng 'YYYY-MM-DD'
    """
    async with get_connection() as conn:
        # Tổng chi
        async with conn.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_expense
            FROM transactions
            WHERE user_id = ? 
              AND type = 'expense'
              AND date(transaction_date) BETWEEN date(?) AND date(?)
        """, (user_id, start_date, end_date)) as cursor:
            row = await cursor.fetchone()
            total_expense = row["total_expense"] if row else 0

        # Tổng thu
        async with conn.execute("""
            SELECT COALESCE(SUM(amount), 0) as total_income
            FROM transactions
            WHERE user_id = ? 
              AND type = 'income'
              AND date(transaction_date) BETWEEN date(?) AND date(?)
        """, (user_id, start_date, end_date)) as cursor:
            row = await cursor.fetchone()
            total_income = row["total_income"] if row else 0

        # Chi tiết theo từng danh mục chi tiêu
        async with conn.execute("""
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? 
              AND type = 'expense'
              AND date(transaction_date) BETWEEN date(?) AND date(?)
            GROUP BY category
            ORDER BY total DESC
        """, (user_id, start_date, end_date)) as cursor:
            rows = await cursor.fetchall()
            categories = {row["category"]: row["total"] for row in rows}

        return {
            "total_expense": total_expense,
            "total_income": total_income,
            "net": total_income - total_expense,
            "categories": categories
        }

async def get_all_transactions(user_id: int, limit: int = 1000) -> List[Dict[str, Any]]:
    """Lấy danh sách các giao dịch để phục vụ xuất Excel."""
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT id, transaction_date, type, amount, category, note
            FROM transactions
            WHERE user_id = ?
            ORDER BY transaction_date DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def set_budget(user_id: int, category: str, monthly_limit: int) -> None:
    """Đặt hoặc cập nhật ngân sách cho một danh mục."""
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO budgets (user_id, category, monthly_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit
        """, (user_id, category, monthly_limit))
        await conn.commit()

async def get_budget_status(user_id: int, category: str) -> Optional[Dict[str, Any]]:
    """Kiểm tra tình trạng ngân sách của danh mục trong tháng hiện tại."""
    first_day_of_month = date.today().replace(day=1).strftime("%Y-%m-%d")

    async with get_connection() as conn:
        # Lấy hạn mức
        async with conn.execute("""
            SELECT monthly_limit FROM budgets
            WHERE user_id = ? AND category = ?
        """, (user_id, category)) as cursor:
            b_row = await cursor.fetchone()
            if not b_row:
                return None
            monthly_limit = b_row["monthly_limit"]

        # Lấy số tiền đã chi trong tháng
        async with conn.execute("""
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM transactions
            WHERE user_id = ? 
              AND category = ?
              AND type = 'expense'
              AND date(transaction_date) >= date(?)
        """, (user_id, category, first_day_of_month)) as cursor:
            s_row = await cursor.fetchone()
            spent = s_row["spent"] if s_row else 0

        percent = (spent / monthly_limit) * 100 if monthly_limit > 0 else 0
        return {
            "monthly_limit": monthly_limit,
            "spent": spent,
            "percent": percent,
            "remaining": monthly_limit - spent
        }

async def get_all_active_user_ids() -> List[int]:
    """Lấy danh sách user IDs để gửi thông báo nhắc nhở."""
    async with get_connection() as conn:
        async with conn.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row["user_id"] for row in rows]

def get_fund_icon(name: str) -> str:
    """Tự động chọn icon thích hợp cho quỹ theo tên."""
    n = name.lower()
    if any(k in n for k in ["tiết kiệm", "saving", "heo", "lợn"]):
        return "🐖"
    if any(k in n for k in ["du lịch", "travel", "nghỉ mát", "chơi", "phượt"]):
        return "🏖️"
    if any(k in n for k in ["khẩn cấp", "dự phòng", "emergency"]):
        return "🆘"
    if any(k in n for k in ["ăn", "uống", "food", "nhậu"]):
        return "🍜"
    if any(k in n for k in ["xe", "mua xe", "bike", "car", "oto", "ô tô"]):
        return "🛵"
    if any(k in n for k in ["nhà", "mua nhà", "house", "homestay"]):
        return "🏠"
    if any(k in n for k in ["đầu tư", "invest", "chứng khoán", "coin"]):
        return "📈"
    if any(k in n for k in ["cưới", "đám cưới", "wedding"]):
        return "💍"
    if any(k in n for k in ["học", "khoá học", "sách", "education"]):
        return "📚"
    if any(k in n for k in ["mua sắm", "shopping", "đồ"]):
        return "🛍️"
    if any(k in n for k in ["sức khỏe", "thuốc", "y tế", "health"]):
        return "💊"
    return "💰"

async def get_user_balance(user_id: int) -> Dict[str, Any]:
    """Lấy thông tin số dư của người dùng."""
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT current_balance, is_balance_initialized
            FROM users
            WHERE user_id = ?
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"current_balance": 0, "is_initialized": False}
            return {
                "current_balance": row["current_balance"] or 0,
                "is_initialized": bool(row["is_balance_initialized"])
            }

async def set_user_balance(user_id: int, new_balance: int) -> int:
    """Cài đặt số dư hiện tại của người dùng."""
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, current_balance, is_balance_initialized)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET 
                current_balance = excluded.current_balance,
                is_balance_initialized = 1
        """, (user_id, new_balance))
        await conn.commit()
        return new_balance

async def create_fund(
    user_id: int,
    name: str,
    initial_balance: int = 0,
    target_amount: int = 0,
    icon: Optional[str] = None
) -> Dict[str, Any]:
    """Tạo mới một quỹ tài chính."""
    clean_name = name.strip()
    if not icon:
        icon = get_fund_icon(clean_name)

    async with get_connection() as conn:
        # Kiểm tra quỹ đã tồn tại chưa (case-insensitive)
        async with conn.execute("""
            SELECT id, name, balance, target_amount, icon
            FROM funds
            WHERE user_id = ? AND LOWER(name) = LOWER(?)
        """, (user_id, clean_name)) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return {
                    "created": False,
                    "fund": dict(existing),
                    "message": f"Quỹ '{existing['name']}' đã tồn tại!"
                }

        cursor = await conn.execute("""
            INSERT INTO funds (user_id, name, balance, target_amount, icon)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, clean_name, initial_balance, target_amount, icon))
        fund_id = cursor.lastrowid

        # Ghi log lịch sử nếu có số dư khởi tạo
        if initial_balance > 0:
            await conn.execute("""
                INSERT INTO fund_logs (fund_id, user_id, action_type, amount, previous_balance, new_balance, note)
                VALUES (?, ?, 'create_fund', ?, 0, ?, 'Khởi tạo quỹ')
            """, (fund_id, user_id, initial_balance, initial_balance))

        await conn.commit()

        return {
            "created": True,
            "fund": {
                "id": fund_id,
                "user_id": user_id,
                "name": clean_name,
                "balance": initial_balance,
                "target_amount": target_amount,
                "icon": icon
            },
            "message": "Tạo quỹ thành công!"
        }

async def set_fund_balance(user_id: int, name: str, new_balance: int) -> Optional[Dict[str, Any]]:
    """Đặt số dư cho một quỹ cụ thể."""
    clean_name = name.strip()
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT id, name, balance, target_amount, icon
            FROM funds
            WHERE user_id = ? AND LOWER(name) = LOWER(?)
        """, (user_id, clean_name)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            fund = dict(row)

        previous_balance = fund["balance"]
        delta = new_balance - previous_balance

        await conn.execute("""
            UPDATE funds
            SET balance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (new_balance, fund["id"], user_id))

        await conn.execute("""
            INSERT INTO fund_logs (fund_id, user_id, action_type, amount, previous_balance, new_balance, note)
            VALUES (?, ?, 'set_balance', ?, ?, ?, 'Cập nhật số dư quỹ')
        """, (fund["id"], user_id, delta, previous_balance, new_balance))

        await conn.commit()

        fund["previous_balance"] = previous_balance
        fund["balance"] = new_balance
        return fund

async def get_fund_by_name(user_id: int, name: str) -> Optional[Dict[str, Any]]:
    """Tìm thông tin quỹ theo tên."""
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT id, name, balance, target_amount, icon, created_at, updated_at
            FROM funds
            WHERE user_id = ? AND LOWER(name) = LOWER(?)
        """, (user_id, name.strip())) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_all_funds(user_id: int) -> List[Dict[str, Any]]:
    """Lấy danh sách tất cả các quỹ của người dùng."""
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT id, name, balance, target_amount, icon, created_at, updated_at
            FROM funds
            WHERE user_id = ?
            ORDER BY balance DESC, id ASC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def delete_fund(user_id: int, fund_name: str) -> bool:
    """Xóa một quỹ theo tên."""
    async with get_connection() as conn:
        cursor = await conn.execute("""
            DELETE FROM funds
            WHERE user_id = ? AND LOWER(name) = LOWER(?)
        """, (user_id, fund_name.strip()))
        await conn.commit()
        return cursor.rowcount > 0

async def get_financial_overview(user_id: int) -> Dict[str, Any]:
    """Lấy tổng quan tài chính: Số dư ví, danh sách các quỹ và tiền tự do."""
    async with get_connection() as conn:
        async with conn.execute("""
            SELECT current_balance, is_balance_initialized
            FROM users
            WHERE user_id = ?
        """, (user_id,)) as cursor:
            user_row = await cursor.fetchone()
            current_balance = user_row["current_balance"] if user_row else 0
            is_initialized = bool(user_row["is_balance_initialized"]) if user_row else False

        async with conn.execute("""
            SELECT id, name, balance, target_amount, icon, created_at, updated_at
            FROM funds
            WHERE user_id = ?
            ORDER BY balance DESC, id ASC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            funds = [dict(row) for row in rows]

        total_funds = sum(f["balance"] for f in funds)
        unallocated = current_balance - total_funds if is_initialized else 0

        return {
            "current_balance": current_balance,
            "is_balance_initialized": is_initialized,
            "funds": funds,
            "total_funds": total_funds,
            "unallocated": unallocated,
        }

