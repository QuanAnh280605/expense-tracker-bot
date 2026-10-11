import io
from typing import Dict
import matplotlib
# Sử dụng backend 'Agg' không cần GUI
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from utils.formatters import format_currency

def generate_pie_chart(categories_data: Dict[str, int], title: str = "Phân Bổ Chi Tiêu") -> io.BytesIO:
    """
    Tạo biểu đồ hình tròn (Pie Chart) biểu diễn tỷ lệ chi tiêu theo danh mục.
    Trả về buffer io.BytesIO chứa file ảnh PNG.
    """
    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)

    labels = list(categories_data.keys())
    values = list(categories_data.values())

    # Bảng màu tươi sáng, hiện đại
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A",
        "#98D8C8", "#F7D794", "#778BEB", "#E77F67", "#CF6A87"
    ]

    # Format hiển thị phần trăm và số tiền
    def autopct_format(pct):
        return f"{pct:.1f}%" if pct > 3 else ""

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct=autopct_format,
        startangle=140,
        colors=colors[:len(labels)],
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2), # Donut chart style
        textprops=dict(color="#2C3E50", fontsize=10, weight="bold")
    )

    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_color("white")
        autotext.set_weight("bold")

    total_amount = sum(values)
    ax.set_title(
        f"{title}\nTổng chi: {format_currency(total_amount)}",
        fontsize=14,
        weight="bold",
        pad=20,
        color="#2C3E50"
    )

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
