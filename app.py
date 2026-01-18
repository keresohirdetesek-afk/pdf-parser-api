from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)

# -------------------------
# Segédfüggvény regexhez
# -------------------------
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

    # =========================
    # 1️⃣ PDF → NYERS SZÖVEG
    # =========================
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        page_texts = []
        for page in pdf.pages:
            t1 = page.extract_text() or ""
            try:
                t2 = page.extract_text(layout=True) or ""
            except TypeError:
                t2 = ""

            # amelyik hosszabb, azt használjuk
            page_texts.append(t2 if len(t2) > len(t1) else t1)

        text = "\n".join(page_texts)

    lines = text.split("\n")

    # =========================
    # 2️⃣ BLOKKOK KIVÁGÁSA
    # =========================

    # ---- FEJLÉC / ENGEDÉLY ----
    header_block = []
    for line in lines[:150]:
        header_block.append(line)
        if "Tengelyadat" in line:
            break

    # ---- ÚTVONAL BLOKK ----
    route_block = []
    route_keywords = ["Útvonal", "útvonal", "Útvonal, megkötések", "Megkötések"]
    stop_keywords = ["Tengelyadat", "Rakomány", "Díjszámítás"]

    capture = False
    for line in lines:
        if any(k in line for k in route_keywords):
            capture = True
        if capture:
            route_block.append(line)
            if any(s in line for s in stop_keywords):
                break

    # ---- TENGELY BLOKK ----
    axle_block = []
    axle_keywords = ["Tengelyadat", "Tengely adatok", "Tengelycsoport", "Tengelyterhel"]

    capture = False
    for line in lines:
        if any(k in line for k in axle_keywords):
            capture = True
        if capture:
            axle_block.append(line)
        if capture and len(axle_block) >= 100:
            break

    axle_joined = " ".join(axle_block)

    # =========================
    # 3️⃣ ALAP MEZŐK (STABIL)
    # =========================

    data = {
        "permit_number": find(r"(UE-[A-Z]-?\d+/\d{4})", text),
        "issue_date": find(r"(\d{4}\.\s?\d{2}\.\s?\d{2})", text),
        "from_place": find(r"Kiindul[aá]s.*?\n.*?\n([A-Za-zÁÉÍÓÖŐÚÜŰ ,\.\-]+)", text),
        "to_place": find(r"Célállomás.*?\n.*?\n([A-Za-zÁÉÍÓÖŐÚÜŰ ,\.\-]+)", text),
        "license_plate": ", ".join(
            set(re.findall(r"\b[A-Z]{2,3}\d{3}\s?[A-Z]\b", text))
        ) or None,
    }

    # Tengelyszám (A, V, E sorok száma)
    axle_count = len(re.findall(r"^\s*\d+\s+[AVE]", axle_joined))
    data["axle_count"] = axle_count if axle_count > 0 else None

    # Tengelycsoportok
    data["axle_groups"] = {
        "VV": find(r"VV\s+([\d,\.]+)", axle_joined),
        "EE": find(r"EE\s+([\d,\.]+)", axle_joined),
    }

    # =========================
    # 4️⃣ DEBUG / TANÍTÁS
    # =========================
    return jsonify({
        "parsed": data,
        "HEADER_RAW": header_block,
        "ROUTE_RAW": route_block,
        "AXLE_RAW": axle_block
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
