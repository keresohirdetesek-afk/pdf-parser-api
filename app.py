from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os
import json
from datetime import datetime

# =========================================
# PDF Parser API – v2 baseline
# From this version we continue development
# + v2.1: /confirm endpoint (save validated data)
# =========================================

app = Flask(__name__)
CORS(app)

def find(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None

def safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", s)[:120]

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "v2.1"})

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    file = request.files["file"]

    # 1) PDF -> text (layout fallback)
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        page_texts = []
        for page in pdf.pages:
            t1 = page.extract_text() or ""
            try:
                t2 = page.extract_text(layout=True) or ""
            except TypeError:
                t2 = ""
            page_texts.append(t2 if len(t2) > len(t1) else t1)

        text = "\n".join(page_texts)

    lines = text.split("\n")

    # 2) Blocks
    header_block = []
    for line in lines[:150]:
        header_block.append(line)
        if "Tengelyadat" in line:
            break

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

    axle_block = []
    axle_keywords = ["Tengelyadat", "Tengely adatok", "Tengelycsoport", "Tengelyterhel"]

    capture = False
    for line in lines:
        if any(k in line for k in axle_keywords):
            capture = True
        if capture:
            axle_block.append(line)
        if capture and len(axle_block) >= 110:
            break

    axle_joined = " ".join(axle_block)

    # 3) Basic parsed fields (lightweight)
    permit_number = find(r"(UE-[A-Z]-?\d+/\d{4})", text)
    issue_date = find(r"(\d{4}\.\s?\d{2}\.\s?\d{2})", text)

    # license plates from vehicle list (first page area) – more robust
    plates = list(dict.fromkeys(re.findall(r"\b[A-Z]{2,3}\d{3}\s?[A-Z]\b", text)))
    license_plate = ", ".join(plates) if plates else None

    # axle_count (rows like "1 A", "2 V", "3 E" inside axle block)
    axle_count = len(re.findall(r"^\s*\d+\s+[AVE]\b", axle_joined, re.MULTILINE))
    axle_count = axle_count if axle_count > 0 else None

    # axle_groups (VV/EE lines)
    axle_groups = {
        "VV": find(r"\bVV\s+([\d,\.]+)", axle_joined),
        "EE": find(r"\bEE\s+([\d,\.]+)", axle_joined),
    }

    # Make a simple document_id for next step (permit+time)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    doc_id = safe_filename((permit_number or file.filename or "doc") + "_" + ts)

    return jsonify({
        "version": "v2.1",
        "document_id": doc_id,
        "parsed": {
            "permit_number": permit_number,
            "issue_date": issue_date,
            "license_plate": license_plate,
            "axle_count": axle_count,
            "axle_groups": axle_groups
        },
        "HEADER_RAW": header_block,
        "ROUTE_RAW": route_block,
        "AXLE_RAW": axle_block
    })


<button
  onClick={saveData}
  className="px-4 py-2 bg-green-600 text-white rounded"
>
  Mentés
</button>









@app.route("/confirm", methods=["POST"])
def confirm():
    """
    Frontend sends back validated / spatial-parsed data.
    We save it to a JSON file on the server (no DB yet).
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Hiányzó JSON body"}), 400

    document_id = payload.get("document_id")
    parsed_validated = payload.get("validated")

    if not document_id or not parsed_validated:
        return jsonify({"error": "Kell: document_id + validated"}), 400

    # Ensure folder exists
    os.makedirs("confirmed", exist_ok=True)

    out_path = os.path.join("confirmed", safe_filename(document_id) + ".json")

    # Add metadata
    to_save = {
        "saved_at_utc": datetime.utcnow().isoformat() + "Z",
        "document_id": document_id,
        "validated": parsed_validated
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "saved": out_path, "document_id": document_id})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)



function saveData() {
  fetch("https://web-production-pilot.up.railway.app/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      data: truckData
    })
  });
}
