from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)

def find(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    file = request.files["file"]

    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        data = {
            "permit_number": find(r"(UE-[A-Z]-\d{5}/\d{4})", text),
            "issue_date": find(r"(\d{4}\.\d{2}\.\d{2})", text),
            "license_plate": find(r"Rendsz[aá]m\s*[:\-]?\s*([A-Z0-9\-]+)", text),
            "from_place": find(r"Kiindul[aá]s\s*[:\-]?\s*(.+)", text),
            "to_place": find(r"C[eé]l\s*[:\-]?\s*(.+)", text),
            "vehicle_type": find(r"J[aá]rm[uű]\s*t[ií]pus\s*[:\-]?\s*(.+)", text),
            "raw_text": text[:4000]
        }

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
