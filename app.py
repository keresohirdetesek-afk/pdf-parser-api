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
            # ENGEDÉLYSZÁM pl. UE-921/2026 vagy UE-A-12345/2024
            "permit_number": find(r"(UE-[A-Z\-]*\d+/\d{4})", text),

            # DÁTUM pl. 2026.01.12
            "issue_date": find(r"(\d{4}\.\d{2}\.\d{2})", text),

            # RENDSZÁM pl. NB548H / ABC-123
            "license_plate": find(r"Rendsz[aá]m\s*[:\-]?\s*([A-Z0-9\- ]+)", text),

            # INDULÁS
            "from_place": find(r"Kiindul[aá]s\s*[:\-]?\s*(.+)", text),

            # CÉL
            "to_place": find(r"C[eé]l\s*[:\-]?\s*(.+)", text),

            # TENGELYSZÁM pl. 3 tengelyes / 5 tengely
            "axle_count": find(r"(\d+)\s*tengely", text),

            # SÚLY pl. 25900 kg / 25,9 t
            "weight": find(r"(\d{2,5}[.,]?\d*)\s*(kg|t)", text),

            # ellenőrzéshez
            "raw_text_preview": text[:2000]
        }

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
