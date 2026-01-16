from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)

def find(pattern, text, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
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

        # ===== ENGEDÉLYSZÁM =====
        permit_number = find(r"(UE-[A-Z]-\d+/\d{4})", text)

        # ===== KIADÁS DÁTUMA =====
        issue_date = find(r"(\d{4}\.\s?\d{2}\.\s?\d{2})", text)

        # ===== RENDSZÁMOK =====
        plates = re.findall(r"\n([A-Z]{2,3}\d{3}\s?[A-Z])\b", text)
        license_plate = ", ".join(plates) if plates else None

        # ===== KIINDULÁS (KÖVETKEZŐ SOR!) =====
        from_place = find(
            r"10\.\s*Kiindulás.*?\n([A-ZÁÉÍÓÖŐÚÜŰa-z0-9 ,\-]+)",
            text
        )

        # ===== CÉLÁLLOMÁS =====
        to_place = find(
            r"12\.\s*Célállomás.*?\n([A-ZÁÉÍÓÖŐÚÜŰa-z0-9 ,\-]+)",
            text
        )

        # ===== TENGELYSZÁM =====
        axle_counts = re.findall(r"nyerges vontató\s+(\d)|félpótkocsi\s+(\d)", text)
        axle_count = sum(int(a or b) for a, b in axle_counts) if axle_counts else None

        # ===== ÖSSZTÖMEG =====
        weight = find(r"Raktömeg\s*\[t\]\s*([\d,]+)", text)

        return jsonify({
            "permit_number": permit_number,
            "issue_date": issue_date,
            "license_plate": license_plate,
            "from_place": from_place,
            "to_place": to_place,
            "axle_count": axle_count,
            "weight": weight,
            "raw_text_preview": text[:2000]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
