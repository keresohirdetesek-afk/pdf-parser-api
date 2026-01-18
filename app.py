from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pdfplumber
import io
import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)
CORS(app)

# -------------------------------------------------
# SEGÉD: PDF SZÖVEG KINYERÉS (STABIL, V2)
# -------------------------------------------------
def extract_text(file_bytes):
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = []
        for page in pdf.pages:
            try:
                t = page.extract_text(layout=True) or ""
            except TypeError:
                t = page.extract_text() or ""
            pages.append(t)
    return "\n".join(pages)

# -------------------------------------------------
# SEGÉD: EGYSZERŰ ADATKINERÉS (NEM OKOS, STABIL)
# -------------------------------------------------
def parse_data(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    def find(pattern):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else "-"

    data = {
        "permit": find(r"(UE-[A-Z]-\d+/\d{4})"),
        "valid_from": find(r"9\.\s.*?(\d{4}\.\s?\d{2}\.\s?\d{2}.*?\d{2}:\d{2})"),
        "valid_to": find(r"C\.\s.*?(\d{4}\.\s?\d{2}\.\s?\d{2}.*?\d{2}:\d{2})"),
        "from_place": find(r"10\.\s.*?\n(.*)"),
        "to_place": find(r"12\.\s.*?\n(.*)"),
        "license_plates": ", ".join(set(re.findall(r"[A-Z]{3}\d{3}\s?[A-Z]?", text))),
    }

    return data

# -------------------------------------------------
# HEALTH
# -------------------------------------------------
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mode": "analyze + pdf export"})

# -------------------------------------------------
# JSON KIÉRTÉKELÉS (DEBUG)
# -------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl"}), 400

    file = request.files["file"]
    text = extract_text(file.read())
    data = parse_data(text)

    return jsonify(data)

# -------------------------------------------------
# PDF GENERÁLÁS (EZ A LÉNYEG)
# -------------------------------------------------
@app.route("/render-pdf", methods=["POST"])
def render_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl"}), 400

    file = request.files["file"]
    text = extract_text(file.read())
    data = parse_data(text)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40

    def line(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(180, y, value)
        y -= 16

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "ÚTVONALENGEDÉLY – ÖSSZEFOGLALÓ")
    y -= 30

    line("Engedélyszám:", data["permit"])
    line("Érvényesség kezdete:", data["valid_from"])
    line("Érvényesség vége:", data["valid_to"])

    y -= 10
    line("Kiindulás:", data["from_place"])
    line("Cél:", data["to_place"])

    y -= 10
    line("Rendszám(ok):", data["license_plates"])

    y -= 30
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, y, "Ez a dokumentum automatikusan generált összefoglaló.")

    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="utvonalengedely_osszegzes.pdf"
    )

# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
