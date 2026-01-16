from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import re
import io

app = Flask(__name__)
CORS(app)  # CORS engedélyezése

# PDF feltöltés és elemzés végpont
@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve."}), 400

    file = request.files["file"]
    
    try:
        # PDF szövegének kinyerése
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""

        # Regular expression minták
        permit_number = re.search(r"(UE-[A-Z]-\d{5}/\d{4})", text)
        from_place = re.search(r"Kiindulás.*?:\s*(.*?)\s*\n", text)
        to_place = re.search(r"Cél.*?:\s*(.*?)\s*\n", text)
        license_plate = re.search(r"Rendszám:?\s*([A-Z0-9-]+)", text)
        issue_date = re.search(r"\d{4}\.\d{2}\.\d{2}", text)
        weight = re.search(r"(Tengelyszám|Súly):?\s*([\d\.,]+)", text)

        # Válasz készítése
        return jsonify({
            "permit_number": permit_number.group(1) if permit_number else None,
            "from_place": from_place.group(1) if from_place else None,
            "to_place": to_place.group(1) if to_place else None,
            "license_plate": license_plate.group(1) if license_plate else None,
            "issue_date": issue_date.group(0) if issue_date else None,
            "weight": weight.group(2) if weight else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = 5000  # vagy bármely más port, amit preferálsz
    app.run(host="0.0.0.0", port=port)
