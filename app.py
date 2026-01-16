from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve."}), 400

    file = request.files["file"]

    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # ===== REGEXEK =====

        permit_number = re.search(r"(UE-\d+/\d{4})", text)

        from_place = re.search(
            r"Kiindul[aá]s.*?:\s*(.+)",
            text,
            re.IGNORECASE
        )

        to_place = re.search(
            r"C[ée]l.*?:\s*(.+)",
            text,
            re.IGNORECASE
        )

        license_plate = re.search(
            r"Rendsz[aá]m.*?:\s*([A-Z0-9\- ]+)",
            text,
            re.IGNORECASE
        )

        vehicle_type = re.search(
            r"J[aá]rm[űu]fajta.*?:\s*(.+)",
            text,
            re.IGNORECASE
        )

        issue_date = re.search(
            r"KIADVA.*?:\s*(\d{4}\.\s*\d{2}\.\s*\d{2})",
            text
        )

        # ===== VÁLASZ =====

        return jsonify({
            "permit_number": permit_number.group(1).strip() if permit_number else None,
            "from_place": from_place.group(1).strip() if from_place else None,
            "to_place": to_place.group(1).strip() if to_place else None,
            "license_plate": license_plate.group(1).strip() if license_plate else None,
            "vehicle_type": vehicle_type.group(1).strip() if vehicle_type else None,
            "issue_date": issue_date.group(1).strip() if issue_date else None,
            "raw_text_preview": text[:2000]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
