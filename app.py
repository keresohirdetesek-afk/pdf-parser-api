from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)

# ---------- SEGÉDFÜGGVÉNY ----------
def find_all(pattern, text):
    return list(set(m.strip() for m in re.findall(pattern, text, re.IGNORECASE)))

def find_one(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None

# ---------- HEALTH CHECK ----------
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

# ---------- PDF FELTÖLTÉS ----------
@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    file = request.files["file"]

    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # --------- ALAPADATOK ----------
        permit_number = find_one(r"(UE-[A-Z]-\d+/\d{4})", text)
        issue_date = find_one(r"(\d{4}\.\s*\d{2}\.\s*\d{2})", text)

        from_place = find_one(
            r"Kiindulás.*?\n.*?\n([A-ZÁÉÍÓÖŐÚÜŰ][^\n]+)",
            text
        )

        to_place = find_one(
            r"Célállomás.*?\n.*?\n([A-ZÁÉÍÓÖŐÚÜŰ][^\n]+)",
            text
        )

        # --------- RENDSZÁMOK ----------
        license_plates = find_all(
            r"\b[A-Z]{2,3}[0-9]{2,3}[A-Z]{1,2}\b",
            text
        )

        # --------- TENGELYEK ----------
        axle_rows = re.findall(
            r"\n(\d+)\s+[A-Z]\s+([0-9,]+)",
            text
        )

        axles = []
        for idx, weight in axle_rows:
            axles.append({
                "axle": int(idx),
                "weight_tons": float(weight.replace(",", "."))
            })

        # --------- TENGELYCSOPORTOK ----------
        axle_groups = {}
        for grp in ["VV", "EE"]:
            m = re.search(rf"{grp}\s+([0-9,]+)", text)
            if m:
                axle_groups[grp] = float(m.group(1).replace(",", "."))

        # --------- ÚTVONAL ----------
        roads = list(set(re.findall(r"\bM\d+\b", text)))

        # --------- KM SZELVÉNY ----------
        km_points = re.findall(
            r"km\s*\d+\+\d+",
            text,
            re.IGNORECASE
        )

        return jsonify({
            "permit_number": permit_number,
            "issue_date": issue_date,
            "from_place": from_place,
            "to_place": to_place,
            "license_plates": license_plates,
            "axles": axles,
            "axle_groups": axle_groups,
            "roads": roads,
            "km_sections": km_points,
            "raw_text_preview": text[:2000]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
