import json
import logging
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from groq import AsyncGroq
from config.settings import settings

logger = logging.getLogger(__name__)

class TransactionItem(BaseModel):
    type: str = Field(description="'expense' cho chi tiêu, 'income' cho thu nhập")
    category: str = Field(description="Một trong các danh mục: Ăn uống, Đi lại, Mua sắm, Nhà cửa, Giải trí, Sức khỏe, Hóa đơn, Lương thưởng, Khác")
    amount: int = Field(description="Số tiền nguyên bằng VND")
    note: str = Field(description="Ghi chú chi tiết món chi/thu")

class ParsedExpenseResponse(BaseModel):
    is_financial: bool = Field(description="True nếu tin nhắn chứa thông tin thu chi tài chính, False nếu là trò chuyện thông thường")
    items: List[TransactionItem] = Field(default_factory=list, description="Danh sách các khoản thu/chi bóc tách được")

class ParsedFinancialAction(BaseModel):
    intent: Literal[
        "record_transaction",
        "set_balance",
        "get_balance",
        "create_fund",
        "set_fund_balance",
        "get_funds",
        "delete_fund",
        "chat"
    ] = Field(description="Ý định của người dùng")
    items: List[TransactionItem] = Field(default_factory=list, description="Danh sách các giao dịch nếu intent là record_transaction")
    balance_amount: Optional[int] = Field(default=None, description="Số tiền thiết lập số dư nếu intent là set_balance")
    fund_name: Optional[str] = Field(default=None, description="Tên quỹ nếu intent liên quan đến quỹ")
    fund_amount: Optional[int] = Field(default=None, description="Số tiền của quỹ (số tiền ban đầu hoặc số dư cần set)")
    reply_message: Optional[str] = Field(default=None, description="Câu phản hồi tự nhiên nếu là hội thoại thông thường hoặc giải thích")

SYSTEM_PROMPT = """Bạn là một trợ lý tài chính thông minh chuyên phân tích và phân loại tin nhắn tiếng Việt của người dùng.
Nhiệm vụ của bạn là nhận diện chính xác Ý ĐỊNH (intent) và trích xuất các tham số tương ứng, trả về DUY NHẤT một chuỗi JSON chuẩn:

Cấu trúc JSON:
{
  "intent": "record_transaction" | "set_balance" | "get_balance" | "create_fund" | "set_fund_balance" | "get_funds" | "delete_fund" | "chat",
  "items": [
    {
      "type": "expense" | "income",
      "category": "Ăn uống" | "Đi lại" | "Mua sắm" | "Nhà cửa" | "Giải trí" | "Sức khỏe" | "Hóa đơn" | "Lương thưởng" | "Khác",
      "amount": 50000,
      "note": "phở bò"
    }
  ],
  "balance_amount": null,
  "fund_name": null,
  "fund_amount": null,
  "reply_message": null
}

HƯỚNG DẪN XÁC ĐỊNH INTENT:
1. "set_balance": Người dùng muốn cài đặt / chỉnh sửa / cập nhật số dư hiện tại trong ví hoặc tài khoản.
   - Ví dụ: "set số dư hiện tại của tôi là 10 triệu", "cài số dư 5 củ", "số dư hiện tại là 20tr", "ví tôi hiện có 2 triệu", "tài khoản còn 500k", "tôi có 15 củ trong tài khoản".
   - -> Điền "balance_amount" (số nguyên VND).

2. "get_balance": Người dùng hỏi xem số dư hiện tại, kiểm tra ví, hỏi còn bao nhiêu tiền.
   - Ví dụ: "số dư của tôi còn bao nhiêu?", "kiểm tra ví", "xem số dư", "tài khoản còn bao nhiêu tiền?".

3. "create_fund": Người dùng muốn tạo / lập / mở một quỹ tài chính mới.
   - Ví dụ: "tạo quỹ Du lịch", "lập quỹ Tiết kiệm với 5 triệu", "tạo quỹ mua xe 10 củ", "mở quỹ khẩn cấp 2tr".
   - -> Điền "fund_name" (tên quỹ chuẩn hóa viết hoa chữ cái đầu), "fund_amount" (số tiền ban đầu nếu có, nếu không thì null).

4. "set_fund_balance": Người dùng muốn đặt / cập nhật / gán số tiền cụ thể cho một quỹ đã có.
   - Ví dụ: "set quỹ tiết kiệm 5 triệu", "đặt quỹ du lịch là 3 củ", "quỹ mua xe có 15tr", "chỉnh quỹ ăn uống thành 2 triệu", "cho quỹ khẩn cấp 5 củ", "quỹ tiết kiệm còn 1 củ".
   - -> Điền "fund_name" (tên quỹ), "fund_amount" (số tiền cần set bằng VND).

5. "get_funds": Người dùng muốn xem danh sách các quỹ, kiểm tra các quỹ.
   - Ví dụ: "xem danh sách quỹ", "các quỹ hiện có", "tôi có những quỹ nào?", "danh sách quỹ", "kiểm tra các quỹ".

6. "delete_fund": Người dùng muốn xóa một quỹ.
   - Ví dụ: "xóa quỹ du lịch", "hủy quỹ tiết kiệm".
   - -> Điền "fund_name" (tên quỹ).

7. "record_transaction": Ghi chép các khoản chi tiêu hoặc thu nhập mới phát sinh hàng ngày.
   - Chi tiêu: "ăn sáng phở bò 45k", "đổ xăng 70k, mua trà sữa 35k", "mua áo 3 lít", "đi chợ hết 200k".
   - Thu nhập: "nhận lương 15 củ", "được thưởng 2tr", "bán đồ cũ 150k", "ai đó trả nợ 500k".
   - Phân biệt với "set_balance": "nhận lương 15tr" là thu nhập phát sinh -> record_transaction; còn "số dư của tôi là 15tr" là thiết lập số dư -> set_balance.

8. "chat": Câu chào, hỏi thăm, trò chuyện không liên quan tài chính ("chào bạn", "hello", "bạn là ai", "hôm nay vui không").
   - -> Điền "reply_message" phản hồi thân thiện, ngắn gọn và có thể gợi ý các tính năng tài chính.

QUY TẮC CHUYỂN ĐỔI SỐ TIỀN & TIẾNG LÓNG VIỆT NAM:
1. "k", "nghìn", "ngàn" = x 1.000 (vd: "45k" -> 45000, "150 nghìn" -> 150000).
2. "lít", "xị" = x 100.000 (vd: "1 lít" -> 100000, "2 lít rưỡi" -> 250000).
3. "củ", "chai", "tr", "m", "triệu" = x 1.000.000 (vd: "1 củ" -> 1000000, "2tr5" -> 2500000, "3 củ 2" -> 3200000, "nửa củ" -> 500000).
4. Các từ chỉ số lượng: "năm chục" = 50000, "trăm rưỡi" = 150000, "hai xị" = 200000.
5. Nếu tin nhắn có nhiều khoản chi tiêu (vd: "ăn trưa 40k, trà sữa 30k"), tách thành nhiều phần tử trong "items".

Chỉ trả về DUY NHẤT chuỗi JSON hợp lệ, không bọc markdown ```json và không có text giải thích bên ngoài.
"""

class GroqService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    async def parse_financial_message(self, text: str) -> ParsedFinancialAction:
        """Phân tích ý định người dùng và bóc tách dữ liệu tài chính."""
        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                model=self.model,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            raw_content = chat_completion.choices[0].message.content.strip()
            data = json.loads(raw_content)
            return ParsedFinancialAction(**data)
        except Exception as e:
            logger.error(f"Lỗi khi gọi Groq API: {e}", exc_info=True)
            return ParsedFinancialAction(intent="chat", reply_message="Xin lỗi, tôi gặp sự cố khi xử lý tin nhắn này. Bạn vui lòng thử lại nhé!")

    async def parse_expense_text(self, text: str) -> ParsedExpenseResponse:
        """Hàm tương thích ngược với code cũ."""
        res = await self.parse_financial_message(text)
        if res.intent == "record_transaction" and res.items:
            return ParsedExpenseResponse(is_financial=True, items=res.items)
        return ParsedExpenseResponse(is_financial=False, items=[])

groq_service = GroqService()
