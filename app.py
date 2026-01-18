from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(__name__)
CORS(app)


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def find_after(label_regex, text):
    """
    Megkeresi a címkét, és a KÖVETKEZŐ sort adja vissza
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(label_regex, line, re.IGNORECASE):
            if i + 1 < len(lines):
                return clean(lines[i + 1])
    return None


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

        # ===== ALAP ADATOK =====

        permit_number = re.search(r"(UE-[A-Z]-\d+/\d{4})", text)
        issue_date = re.search(r"(\d{4}\.\s*\d{2}\.\s*\d{2})", text)

        from_place = find_after(r"10\.\s*Kiindulás", text)
        to_place = find_after(r"12\.\s*Célállomás", text)

        # ===== RENDSZÁMOK =====
        plates = re.findall(r"\b[A-Z]{3}\d{3}\s?[A-Z]\b", text)
        license_plate = ", ".join(sorted(set(plates))) if plates else None

        # ===== TENGELYADATOK =====
        axle_rows = []
        axle_group_totals = {}

        axle_section = False
        for line in text.splitlines():
            if "25. Tengelyadatok" in line:
                axle_section = True
                continue

            if axle_section:
                if re.match(r"\d+\s+[AVE]", line):
                    parts = clean(line).split(" ")
                    axle_rows.append({
                        "axle_no": parts[0],
                        "type": parts[1],
                        "requested_t": parts[2],
                        "allowed_t": parts[3] if len(parts) > 3 else None
                    })

                elif re.match(r"(VV|EE)", line):
                    p = clean(line).split(" ")
                    axle_group_totals[p[0]] = p[1]

                elif line.strip() == "":
                    break

        return jsonify({
            "permit_number": permit_number.group(1) if permit_number else None,
            "issue_date": issue_date.group(1) if issue_date else None,
            "from_place": from_place,
            "to_place": to_place,
            "license_plate": license_plate,
            "axles": axle_rows,
            "axle_groups": axle_group_totals,
            "axle_count": len(axle_rows),
            "raw_text_preview": text[:2000]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
