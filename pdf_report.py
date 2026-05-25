"""Generate PDF analysis report."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image
from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


DISEASE_ORDER = ["Oʻpka tuberkulyozi", "Oʻpka pnevmoniyasi", "Oʻpka pnevmotoraksi"]


def _image_to_reader(image: Image.Image, max_size: int = 800):
    from reportlab.lib.utils import ImageReader

    img = image.copy()
    img.thumbnail((max_size, max_size))
    buf = BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def build_report(
    *,
    output_path: str | Path,
    bemor_ismi: str,
    yosh: str,
    jinsi: str,
    shifokor: str,
    sana: str,
    scores: dict[str, float],
    xulosa: str,
    original_image: Image.Image,
    heatmap_image: Image.Image | None = None,
) -> Path:
    output_path = Path(output_path)
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    # Title
    c.setFillColor(HexColor("#1e3a5f"))
    c.rect(0, height - 2.5 * cm, width, 2.5 * cm, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 1.6 * cm, "TAHLIL — Oʻpka rentgen hisoboti")
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 2.2 * cm, f"Sana: {sana}")

    # Patient info
    c.setFillColor(black)
    y = height - 3.5 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Bemor maʼlumotlari")
    y -= 0.6 * cm
    c.setFont("Helvetica", 11)
    rows = [
        ("Ismi:", bemor_ismi or "—"),
        ("Yoshi:", yosh or "—"),
        ("Jinsi:", jinsi or "—"),
        ("Shifokor:", shifokor or "—"),
    ]
    for label, value in rows:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2 * cm, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(4.5 * cm, y, value)
        y -= 0.5 * cm

    # Images
    y -= 0.3 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Rentgen tasviri")
    y -= 0.4 * cm

    img_w = 7.5 * cm
    img_h = 7.5 * cm
    img_y = y - img_h
    c.drawImage(_image_to_reader(original_image), 2 * cm, img_y, width=img_w, height=img_h, preserveAspectRatio=True, anchor="c")
    if heatmap_image is not None:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(11 * cm, y, "Issiqlik xaritasi (AI eʼtibor zonasi)")
        c.drawImage(_image_to_reader(heatmap_image), 11 * cm, img_y, width=img_w, height=img_h, preserveAspectRatio=True, anchor="c")
    y = img_y - 0.5 * cm

    # Results
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Tahlil natijasi")
    y -= 0.7 * cm

    for name in DISEASE_ORDER:
        value = scores.get(name, 0.0)
        pct = value * 100
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, y, name)
        c.setFont("Helvetica", 11)
        c.drawRightString(width - 2 * cm, y, f"{pct:.1f}%")
        bar_y = y - 0.3 * cm
        bar_w = width - 4 * cm
        c.setStrokeColor(HexColor("#cccccc"))
        c.setFillColor(HexColor("#eeeeee"))
        c.rect(2 * cm, bar_y, bar_w, 0.3 * cm, fill=1, stroke=0)
        color = HexColor("#ff5252") if value >= 0.5 else HexColor("#4caf50")
        c.setFillColor(color)
        c.rect(2 * cm, bar_y, bar_w * min(max(value, 0), 1), 0.3 * cm, fill=1, stroke=0)
        c.setFillColor(black)
        y = bar_y - 0.7 * cm

    # Verdict
    y -= 0.3 * cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Xulosa")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    for line in _wrap(xulosa, 95):
        c.drawString(2 * cm, y, line)
        y -= 0.4 * cm

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(HexColor("#777777"))
    c.drawString(
        2 * cm,
        1.5 * cm,
        "Eslatma: bu hisobot yordamchi tahlil natijasi. Yakuniy tashxis shifokor tomonidan qoʻyiladi.",
    )
    c.drawRightString(width - 2 * cm, 1.5 * cm, "Tahlil v1.0")

    c.showPage()
    c.save()
    return output_path


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= width:
            current = (current + " " + word).strip()
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def default_filename(bemor_ismi: str) -> str:
    safe = "".join(ch for ch in bemor_ismi if ch.isalnum() or ch in "._- ").strip().replace(" ", "_")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = safe or "bemor"
    return f"tahlil_{base}_{stamp}.pdf"
