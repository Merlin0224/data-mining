from pathlib import Path
from statistics import median

from PIL import Image, ImageDraw, ImageFont


OUT = Path("output")
OUT.mkdir(parents=True, exist_ok=True)

A = [21, 16, 19, 24, 27, 23, 22, 21, 20, 17, 16, 20, 23, 22, 18, 24, 26, 25, 20, 26]
B = [38, 24, 38, 45, 46, 44, 42, 34, 40, 30, 31, 40, 40, 32, 36, 42, 50, 47, 46, 50]

FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


NAVY = "#153B5B"
BLUE = "#2E75B6"
PALE_BLUE = "#DDEBF7"
ORANGE = "#E07A2D"
GRID = "#D8E0E8"
TEXT = "#17212B"
MUTED = "#5D6B78"


def draw_centered(draw, xy, text, fnt, fill=TEXT):
    box = draw.textbbox((0, 0), text, font=fnt)
    w = box[2] - box[0]
    h = box[3] - box[1]
    draw.text((xy[0] - w / 2, xy[1] - h / 2), text, font=fnt, fill=fill)


def five_number_summary(values):
    ordered = sorted(values)
    lower = ordered[: len(ordered) // 2]
    upper = ordered[len(ordered) // 2 :]
    return ordered[0], median(lower), median(ordered), median(upper), ordered[-1]


def create_boxplot():
    width, height = 1800, 1050
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)

    d.text((110, 65), "Product A Sales - Boxplot", font=font(52, True), fill=NAVY)
    d.text(
        (110, 132),
        "20 monthly observations; unit: hundreds of yuan",
        font=font(27),
        fill=MUTED,
    )

    left, right = 160, 1640
    axis_y = 770
    x_min, x_max = 14, 29

    def sx(value):
        return left + (value - x_min) / (x_max - x_min) * (right - left)

    for tick in range(x_min, x_max + 1):
        x = sx(tick)
        d.line((x, 250, x, axis_y), fill=GRID, width=2)
        d.line((x, axis_y, x, axis_y + 14), fill=NAVY, width=3)
        draw_centered(d, (x, axis_y + 48), str(tick), font(24), fill=TEXT)

    d.line((left, axis_y, right, axis_y), fill=NAVY, width=4)
    draw_centered(d, ((left + right) / 2, 865), "Monthly sales (hundreds of yuan)", font(29, True), fill=NAVY)

    low, q1, med, q3, high = five_number_summary(A)
    cy = 500
    box_h = 180

    d.line((sx(low), cy, sx(high), cy), fill=NAVY, width=8)
    for endpoint in (low, high):
        x = sx(endpoint)
        d.line((x, cy - 70, x, cy + 70), fill=NAVY, width=8)

    d.rounded_rectangle(
        (sx(q1), cy - box_h / 2, sx(q3), cy + box_h / 2),
        radius=12,
        fill=PALE_BLUE,
        outline=BLUE,
        width=7,
    )
    d.line((sx(med), cy - box_h / 2, sx(med), cy + box_h / 2), fill=ORANGE, width=10)

    labels = [
        (low, "Min = 16", cy + 135),
        (q1, "Q1 = 19.5", cy - 145),
        (med, "Median = 21.5", cy + 135),
        (q3, "Q3 = 24", cy - 145),
        (high, "Max = 27", cy + 135),
    ]
    for value, label, y in labels:
        draw_centered(d, (sx(value), y), label, font(25, value in (q1, med, q3)), fill=ORANGE if value == med else TEXT)

    d.text((110, 955), "Tukey quartiles (median-of-halves); IQR = 4.5; no outliers.", font=font(25), fill=MUTED)
    img.save(OUT / "hw1_3b_boxplot_product_A.png", quality=95, dpi=(180, 180))


def create_scatterplot():
    width, height = 1800, 1200
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)

    d.text((120, 60), "Product A vs. Product B Monthly Sales", font=font(52, True), fill=NAVY)
    d.text((120, 128), "Scatter plot for 20 paired monthly observations", font=font(27), fill=MUTED)

    left, right = 190, 1660
    top, bottom = 220, 1010
    x_min, x_max = 14, 29
    y_min, y_max = 20, 55

    def sx(value):
        return left + (value - x_min) / (x_max - x_min) * (right - left)

    def sy(value):
        return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

    for tick in range(x_min, x_max + 1):
        x = sx(tick)
        d.line((x, top, x, bottom), fill=GRID, width=2)
        d.line((x, bottom, x, bottom + 12), fill=NAVY, width=3)
        draw_centered(d, (x, bottom + 42), str(tick), font(22), fill=TEXT)

    for tick in range(y_min, y_max + 1, 5):
        y = sy(tick)
        d.line((left, y, right, y), fill=GRID, width=2)
        d.line((left - 12, y, left, y), fill=NAVY, width=3)
        draw_centered(d, (left - 50, y), str(tick), font(22), fill=TEXT)

    d.line((left, top, left, bottom), fill=NAVY, width=4)
    d.line((left, bottom, right, bottom), fill=NAVY, width=4)

    n = len(A)
    mean_a = sum(A) / n
    mean_b = sum(B) / n
    slope = sum((a - mean_a) * (b - mean_b) for a, b in zip(A, B)) / sum((a - mean_a) ** 2 for a in A)
    intercept = mean_b - slope * mean_a
    x1, x2 = min(A), max(A)
    d.line((sx(x1), sy(slope * x1 + intercept), sx(x2), sy(slope * x2 + intercept)), fill=ORANGE, width=6)

    offsets = [(-24, -46), (16, 10), (-28, 14), (12, -48), (16, -4), (-48, -42), (14, -48), (-42, 10),
               (14, -42), (12, -42), (-42, 10), (-44, 8), (12, 10), (12, 10), (-44, 8), (14, 10),
               (-48, -38), (12, -46), (12, 10), (12, 10)]
    for month, (a, b) in enumerate(zip(A, B), start=1):
        x, y = sx(a), sy(b)
        d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=BLUE, outline="white", width=3)
        dx, dy = offsets[month - 1]
        d.text((x + dx, y + dy), str(month), font=font(18, True), fill=NAVY)

    draw_centered(d, ((left + right) / 2, 1110), "Product A sales (hundreds of yuan)", font(29, True), fill=NAVY)
    y_label = Image.new("RGBA", (640, 70), (255, 255, 255, 0))
    yd = ImageDraw.Draw(y_label)
    yd.text((0, 8), "Product B sales (hundreds of yuan)", font=font(29, True), fill=NAVY)
    y_label = y_label.rotate(90, expand=True)
    img.paste(y_label, (35, 360), y_label)

    d.rounded_rectangle((1160, 845, 1615, 955), radius=16, fill="#F6F8FA", outline=GRID, width=3)
    d.line((1200, 892, 1280, 892), fill=ORANGE, width=6)
    d.text((1300, 873), "Linear fit", font=font(24), fill=TEXT)
    d.text((1200, 915), "Pearson r = 0.831 (positive)", font=font(24, True), fill=NAVY)

    d.text((120, 1150), "Point labels indicate month numbers 1-20.", font=font(24), fill=MUTED)
    img.save(OUT / "hw1_3e_scatter_A_vs_B.png", quality=95, dpi=(180, 180))


if __name__ == "__main__":
    create_boxplot()
    create_scatterplot()
