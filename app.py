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

        permit_number = re.search(r"(UE-[A-Z]-\d{5}/\d{4})", text)
        from_place = re.search(r"Kiindulás.*?:\s*(.*?)\s*\n", text)
        to_place = re.search(r"Cél.*?:\s*(.*?)\s*\n", text)

        return jsonify({
            "permit_number": permit_number.group(1) if permit_number else None,
            "from_place": from_place.group(1) if from_place else None,
            "to_place": to_place.group(1) if to_place else None,
            "raw_text": text[:4000]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

