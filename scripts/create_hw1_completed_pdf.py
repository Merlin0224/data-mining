from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


SOURCE = Path("/Users/rrsausage/Library/Containers/com.tencent.qq/Data/Downloads/hw1.pdf")
BOXPLOT = Path("output/hw1_3b_boxplot_product_A.png")
SCATTER = Path("output/hw1_3e_scatter_A_vs_B.png")
OUTPUT = Path("output/pdf/hw1_completed_with_figures.pdf")


def figure_page(title, subtitle, image_path, note):
    packet = BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    width, height = letter

    c.setFillColor(HexColor("#153B5B"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(48, height - 54, title)
    c.setFillColor(HexColor("#5D6B78"))
    c.setFont("Helvetica", 10.5)
    c.drawString(48, height - 73, subtitle)

    img = ImageReader(str(image_path))
    iw, ih = img.getSize()
    max_w = width - 72
    max_h = height - 155
    scale = min(max_w / iw, max_h / ih)
    draw_w = iw * scale
    draw_h = ih * scale
    x = (width - draw_w) / 2
    y = 76 + (max_h - draw_h) / 2
    c.drawImage(img, x, y, draw_w, draw_h, preserveAspectRatio=True, mask="auto")

    c.setStrokeColor(HexColor("#D8E0E8"))
    c.line(48, 55, width - 48, 55)
    c.setFillColor(HexColor("#5D6B78"))
    c.setFont("Helvetica", 9)
    c.drawString(48, 39, note)
    c.drawRightString(width - 48, 39, "HW1 - Supplemental figure")
    c.save()
    packet.seek(0)
    return PdfReader(packet).pages[0]


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    for page in PdfReader(str(SOURCE)).pages:
        writer.add_page(page)

    writer.add_page(
        figure_page(
            "3(b) Boxplot - Product A",
            "Tukey quartiles (median-of-halves): min 16, Q1 19.5, median 21.5, Q3 24, max 27; no outliers.",
            BOXPLOT,
            "Sales unit: hundreds of yuan. IQR = 4.5; fences = 12.75 and 30.75.",
        )
    )
    writer.add_page(
        figure_page(
            "3(e) Scatter Plot - Product A vs. Product B",
            "Twenty paired monthly observations; point labels are month numbers; Pearson r = 0.831.",
            SCATTER,
            "The upward pattern indicates a strong positive correlation; correlation does not imply causation.",
        )
    )

    with OUTPUT.open("wb") as stream:
        writer.write(stream)


if __name__ == "__main__":
    main()

