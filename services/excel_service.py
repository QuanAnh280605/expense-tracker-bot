import io
from typing import List, Dict, Any
import pandas as pd
from utils.formatters import format_datetime_vn

def export_transactions_to_excel(transactions: List[Dict[str, Any]]) -> io.BytesIO:
    """Xuất danh sách giao dịch ra file Excel (.xlsx) trong bộ nhớ."""
    if not transactions:
        df = pd.DataFrame(columns=["ID", "Thời Gian", "Loại", "Số Tiền (VNĐ)", "Danh Mục", "Ghi Chú"])
    else:
        formatted_data = []
        for t in transactions:
            type_label = "Chi tiêu" if t["type"] == "expense" else "Thu nhập"
            formatted_data.append({
                "ID": t["id"],
                "Thời Gian": format_datetime_vn(t["transaction_date"]),
                "Loại": type_label,
                "Số Tiền (VNĐ)": t["amount"],
                "Danh Mục": t["category"],
                "Ghi Chú": t["note"] or ""
            })
        df = pd.DataFrame(formatted_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Lịch Sử Thu Chi")
    output.seek(0)
    return output
