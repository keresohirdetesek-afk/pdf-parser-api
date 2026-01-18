from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)

# egyszerű memória "adatbázis"
SAVED = []

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

        def find(pattern):
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            return m.group(1).strip() if m else None

        data = {
            "permit_number": find(r"(UE-[A-Z]-\d+/\d{4})"),
            "issue_date": find(r"(\d{4}\.\s?\d{2}\.\s?\d{2})"),
            "from_place": find(r"Kiindul[aá]s.*?\n.*?([A-ZÁÉÍÓÖŐÚÜŰ].+)"),
            "to_place": find(r"Célállomás.*?\n.*?([A-ZÁÉÍÓÖŐÚÜŰ].+)"),
            "license_plate": ", ".join(set(re.findall(r"[A-Z]{3}\d{3}\s?[A-Z]?", text))),
            "raw_text_preview": text[:2000]
        }

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/confirm", methods=["POST"])
def confirm():
    SAVED.append(request.json)
    return jsonify({"ok": True, "count": len(SAVED)})


@app.route("/list", methods=["GET"])
def list_saved():
    return jsonify(SAVED)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
