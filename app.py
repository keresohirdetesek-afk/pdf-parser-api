from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve."}), 400

    file = request.files["file"]
    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        # Engedélyszám (pl. UE-E-12345/2025)
        permit_number = re.search(r"(UE-[A-Z]-\d{5}/\d{4})", text)

        # Indulás helye
        from_place = re.search(r"Kiindulás.*?:\s*(.*?)\s*\n", text)

        # Célállomás helye
        to_place = re.search(r"Cél.*?:\s*(.*?)\s*\n", text)

        # Rendszám
        license_plate = re.search(r"Rendsz[aá]m\s*[:\-]?\s*([A-Z0-9\-]+)", text)

        # Dátum (pl. 2026.01.12)
        issue_date = re.search(r"(\d{4}\.\d{2}\.\d{2})", text)

        # Tengelyszám (pl. 5 tengelyes)
        axle_number = re.search(r"Tengelysz[aá]m.*?:\s*(.*?)\s*\n", text)

        # Szállítmányozó cég (pl. King Heavy Transport)
        company_name = re.search(r"Szállítmányozó\s*[:\-]?\s*(.*?)\s*\n", text)

        # További mezők, ha szükséges:
        vehicle_type = re.search(r"Jármű típus.*?:\s*(.*?)\s*\n", text)

        # Válasz készítése
        return jsonify({
            "permit_number": permit_number.group(1) if permit_number else None,
            "from_place": from_place.group(1) if from_place else None,
            "to_place": to_place.group(1) if to_place else None,
            "license_plate": license_plate.group(1) if license_plate else None,
            "issue_date": issue_date.group(1) if issue_date else None,
            "axle_number": axle_number.group(1) if axle_number else None,
            "company_name": company_name.group(1) if company_name else None,
            "vehicle_type": vehicle_type.group(1) if vehicle_type else None,
            "raw_text": text[:4000]  # A szöveg első 4000 karaktere a teszteléshez
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
