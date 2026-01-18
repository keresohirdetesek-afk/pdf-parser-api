from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

APP_VERSION = "2026-01-16-STRUCTURED-PARSER"

app = Flask(__name__)
CORS(app)

def clean(text):
    return re.sub(r"\s+", " ", text).strip() if text else None

def find(pattern, text, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return clean(m.group(1)) if m else None

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "version": APP_VERSION
    })

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    file = request.files["file"]

    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages)

        # =========================
        # ALAP ADATOK
        # =========================

        permit_number = find(r"(UE-[A-Z]-\d+/\d{4})", text)
        issue_date = find(r"(\d{4}\.\s?\d{2}\.\s?\d{2})", text)

        # =========================
        # INDULÁS / CÉL – SORSZÁM ALAPÚ
        # =========================

        from_place = find(
            r"10\.\s*Kiindulás\s*\(helységnév.*?\)\s*\n[^\n]*\n([A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű ,\-()]+)",
            text
        )

        to_place = find(
            r"12\.\s*Célállomás\s*\(helységnév.*?\)\s*\n[^\n]*\n([A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű ,\-()]+)",
            text
        )

        # =========================
        # RENDSZÁMOK (TÖBB IS)
        # =========================

        license_plates = list(set(
            re.findall(r"\b[A-Z]{2,3}\d{2,3}[A-Z]{2,3}\b", text)
        ))

        # =========================
        # TENGELYEK – EGYENKÉNT
        # =========================

        axle_lines = re.findall(
            r"^\s*(\d+)\s+([AEV])\s+(X\s+)?([\d,]+)",
            text,
            re.MULTILINE
        )

        axles = []
        for idx, typ, driven, weight in axle_lines:
            axles.append({
                "index": int(idx),
                "type": typ,
                "driven": bool(driven),
                "load_t": float(weight.replace(",", "."))
            })

        # =========================
        # TENGELYCSOPORTOK (VV, EE)
        # =========================

        axle_groups = []
        for code in ["VV", "EE"]:
            m = re.search(rf"{code}\s+([\d,]+)", text)
            if m:
                axle_groups.append({
                    "group": code,
                    "load_t": float(m.group(1).replace(",", "."))
                })

        # =========================
        # TENGELYSZÁM
        # =========================

        axle_count = len(axles)

        # =========================
        # ÚTVONAL / KM SZÖVEG
        # =========================

        route_text = find(
            r"Útvonalengedély.*?\n(.+?)(?:\n\d+\.)",
            text,
            re.DOTALL
        )

        # =========================
        # VÁLASZ
        # =========================

        return jsonify({
            "version": APP_VERSION,
            "permit_number": permit_number,
            "issue_date": issue_date,
            "from_place": from_place,
            "to_place": to_place,
            "license_plates": license_plates,
            "axle_count": axle_count,
            "axles": axles,
            "axle_groups": axle_groups,
            "route_text": route_text,
            "raw_text_preview": text[:2000]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
