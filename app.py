from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import os

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "version": "v2-raw-blocks + permit"
    })


@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    file = request.files["file"]

    header_block = []
    route_block = []
    axle_block = []

    # --- PDF beolvasás ---
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        pages_text = []
        for page in pdf.pages:
            try:
                t = page.extract_text(layout=True) or ""
            except TypeError:
                t = page.extract_text() or ""
            pages_text.append(t)

    text = "\n".join(pages_text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # ===== 1️⃣ FEJLÉC BLOKK =====
    header_block = lines[:120]

    # ===== 2️⃣ ÚTVONAL BLOKK =====
    route_keys = ["Útvonal", "útvonal", "Útvonal, megkötések", "Megkötések"]
    capture = False
    for line in lines:
        if any(k in line for k in route_keys):
            capture = True
        if capture:
            route_block.append(line)
        if capture and len(route_block) >= 50:
            break

    # ===== 3️⃣ TENGELY BLOKK =====
    axle_keys = ["Tengelyadat", "Tengely adatok", "Tengelycsoport", "Tengelyterhel"]
    capture = False
    for line in lines:
        if any(k in line for k in axle_keys):
            capture = True
        if capture:
            axle_block.append(line)
        if capture and len(axle_block) >= 120:
            break

    # ===== 4️⃣ ENGEDÉLYSZÁM (EGYSZERŰ, STABIL) =====
    permit_number = None
    for line in header_block:
        if "UE-" in line and "/" in line:
            permit_number = line
            break

    return jsonify({
        "VERSION": "v2-raw-blocks + permit",
        "permit_number": permit_number,
        "HEADER_RAW": header_block,
        "ROUTE_RAW": route_block,
        "AXLE_RAW": axle_block
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
