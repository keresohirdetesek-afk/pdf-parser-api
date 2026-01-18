from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
import re
import io
import os

app = Flask(__name__)
CORS(app)

# ---------- PDF TEXT EXTRACTION ----------
def extract_text(file_bytes):
    text = ""

    # Normál PDF
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for p in pdf.pages:
                if p.extract_text():
                    text += p.extract_text() + "\n"
    except:
        pass

    # OCR fallback
    if len(text.strip()) < 100:
        images = convert_from_bytes(file_bytes)
        for img in images:
            text += pytesseract.image_to_string(img, lang="hun") + "\n"

    return text


# ---------- AXLE PARSER ----------
def parse_axles(text):
    axles = []
    groups = []

    lines = text.splitlines()

    for line in lines:
        m = re.match(r"\s*(\d+)\s+([AEV])\s+([\d,\.]+)", line)
        if m:
            axles.append({
                "index": int(m.group(1)),
                "type": m.group(2),
                "load_tons": float(m.group(3).replace(",", "."))
            })

        g = re.match(r"\s*(VV|EE|VE|EV)\s+([\d,\.]+)", line)
        if g:
            groups.append({
                "group": g.group(1),
                "load_tons": float(g.group(2).replace(",", "."))
            })

    return axles, groups


# ---------- KM SEGMENT PARSER ----------
def parse_km_segments(text):
    segments = []

    pattern = r"(M\d+)[^\d]*(\d+)\s*\+\s*(\d+)"
    for m in re.finditer(pattern, text):
        km = int(m.group(2)) + int(m.group(3)) / 1000
        segments.append({
            "road": m.group(1),
            "km": round(km, 3)
        })

    return segments


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    file_bytes = request.files["file"].read()
    text = extract_text(file_bytes)

    axles, axle_groups = parse_axles(text)
    km_segments = parse_km_segments(text)

    return jsonify({
        "version": "2026-01-16-FULL-STRUCTURED",
        "permit_number": re.search(r"(UE-[A-Z]-\d+/\d{4})", text).group(1) if re.search(r"(UE-[A-Z]-\d+/\d{4})", text) else None,
        "issue_date": re.search(r"(\d{4}\.\s*\d{2}\.\s*\d{2})", text).group(1) if re.search(r"(\d{4}\.\s*\d{2}\.\s*\d{2})", text) else None,
        "axle_count": len(axles),
        "axles": axles,
        "axle_groups": axle_groups,
        "km_segments": km_segments,
        "raw_text_preview": text[:2000]
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
