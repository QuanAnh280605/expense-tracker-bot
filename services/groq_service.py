import json
from typing import List, Optional
from pydantic import BaseModel, Field
from groq import AsyncGroq
from config.settings import settings

class TransactionItem(BaseModel):
    type: str = Field(description="'expense' cho chi tiêu, 'income' cho thu nhập")
    category: str = Field(description="Một trong các danh mục: Ăn uống, Đi lại, Mua sắm, Nhà cửa, Giải trí, Sức khỏe, Hóa đơn, Lương thưởng, Khác")
    amount: int = Field(description="Số tiền nguyên bằng VND")
    note: str = Field(description="Ghi chú chi tiết món chi/thu")

class ParsedExpenseResponse(BaseModel):
    is_financial: bool = Field(description="True nếu tin nhắn chứa thông tin thu chi tài chính, False nếu là trò chuyện thông thường")
    items: List[TransactionItem] = Field(default_factory=list, description="Danh sách các khoản thu/chi bóc tách được")

SYSTEM_PROMPT = """Bạn là một trợ lý tài chính thông minh chuyên trích xuất dữ liệu thu chi từ tin nhắn tiếng Việt của người dùng.
Nhiệm vụ của bạn là phân tích câu chat và trả về DUY NHẤT một chuỗi JSON chuẩn theo cấu trúc sau:

{
  "is_financial": true/false,
  "items": [
    {
      "type": "expense" | "income",
      "category": "Ăn uống" | "Đi lại" | "Mua sắm" | "Nhà cửa" | "Giải trí" | "Sức khỏe" | "Hóa đơn" | "Lương thưởng" | "Khác",
      "amount": 50000,
      "note": "phở bò"
    }
  ]
}

Quy tắc chuyển đổi số tiền & tiếng lóng tiếng Việt:
1. "k" hoặc "nghìn" = x 1.000 (vd: "45k" -> 45000, "150 nghìn" -> 150000).
2. "lít", "xị" = x 100.000 (vd: "1 lít" -> 100000, "2 lít rưỡi" -> 250000).
3. "củ", "chai", "tr", "m", "triệu" = x 1.000.000 (vd: "1 củ" -> 1000000, "2tr5" -> 2500000, "3 củ 2" -> 3200000).
4. Các từ chỉ số lượng: "năm chục" = 50000, "trăm rưỡi" = 150000, "hai xị" = 200000.
5. Nếu câu có nhiều khoản (vd: "ăn trưa 40k, mua trà sữa 35k"), hãy tách thành từng phần tử riêng biệt trong danh sách "items".
6. Phân loại loại giao dịch:
   - "income": lương, thưởng, bán đồ cũ, ai đó trả nợ, tiền tip, hoa hồng...
   - "expense": tất cả các khoản chi tiêu thông thường.
7. Nếu tin nhắn là câu chào, hỏi thăm, không liên quan đến tiền bạc (vd: "chào bạn", "hôm nay thế nào"), đặt "is_financial": false và "items": [].

Chỉ trả về JSON thuần túy, không kèm bất kỳ lời giải thích nào khác.
"""

class GroqService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    async def parse_expense_text(self, text: str) -> ParsedExpenseResponse:
        """Gọi Groq API để bóc tách thông tin thu chi từ văn bản người dùng."""
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
            raw_content = chat_completion.choices[0].message.content
            data = json.loads(raw_content)
            return ParsedExpenseResponse(**data)
        except Exception as e:
            # Fallback nếu có lỗi phân tích
            return ParsedExpenseResponse(is_financial=False, items=[])

groq_service = GroqService()
