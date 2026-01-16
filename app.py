from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

app = Flask(name)
CORS(app)

def find(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    f = request.files["file"]

    try:
        with pdfplumber.open(io.BytesIO(f.read())) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)

        # =========================
        # 1) ALAP MEZŐK
        # =========================
        permit_number = find(r"(UE-[A-Z]-\d+/\d{4}|UE-\d+/\d{4})", text)
        issue_date = find(r"(\d{4}\.\d{2}\.\d{2})", text)

        # =========================
        # 2) KIINDULÁS + CÉL
        # (ez a PDF layout miatt: dátum + idő a sor elején, helynév a sor végén)
        # =========================
        from_place = find(
            r"10\.\s*Kiindulás.?\n\s\d{4}\.\s*\d{2}\.\s*\d{2}\.\s*\d{1,2}:\d{2}\s+(.+)",
            text
        )
        to_place = find(
            r"12\.\s*Célállomás.?\n\s\d{4}\.\s*\d{2}\.\s*\d{2}\.\s*\d{1,2}:\d{2}\s+(.+)",
            text
        )

        # =========================
        # 3) RENDSZÁMOK (HU/RO/vegyes)
        # A te mintáid: "PBB404 H", "WBD548 H", "BN11RTM RO", "BN15NOU RO"
        # =========================
        plates = re.findall(r"\b([A-Z]{2,3}\d{3}\s?[A-Z]|\b[A-Z]{2}\d{2}[A-Z]{3}\s?RO)\b", text)
        # A fenti két minta:
        # - HU jelleg: PBB404 H / WBD548 H (3 betű + 3 szám + betű)
        # - RO jelleg: BN11RTM RO (2 betű + 2 szám + 3 betű + RO)
        # (ha később más ország is kell, bővítjük)
        plates = [p.strip() for p in plates]
        license_plate = ", ".join(dict.fromkeys(plates)) if plates else None  # de-dup, sorrend marad

        # =========================
        # 4) TENGELYSZÁM (a "Járművek" sorokból)
        # nyerges vontató 3
        # félpótkocsi 5
        # => összesen 8
        # =========================
        axle_nums = re.findall(r"\b(nyerges\s+vontató|félpótkocsi)\s+(\d)\b", text, flags=re.IGNORECASE)
        axle_count = sum(int(n) for _, n in axle_nums) if axle_nums else None

        # =========================
        # 5) RAKTÖMEG / SÚLY [t]
        # "21. Raktömeg [t]" után jellemzően a következő sorban van a szám
        # =========================
        weight = find(r"21\.\s*Raktömeg\s*\[t\].?\n.?([0-9]+,[0-9]+)", text)

        # =========================
        # 6) TENGELYTERHELÉSEK (1..N sorok)
        # példád:
        # 1 A 8,000 ...
        # 2 V 2,780 ...
        # 3 V X 1,320 ...
        # 4 E 8,400 ...
        # 5 E 1,410 ...
        # =========================
        axles = []
        axle_lines = re.findall(r"\n(\d+)\s+([A-Z]{1,2})\s+(X\s+)?([0-9]+,[0-9]+)", text)
        for idx, typ, driven, load in axle_lines:
            # tipikus tengelybetűk: A, V, E (de hagyjuk általánosra)
            # load = első szám a sorban (igényelt/korrigált érték)
            axles.append({
                "index": int(idx),
                "type": typ.strip(),
                "driven": True if driven else False,
                "requested_t": load
            })

        # =========================
        # 7) TENGELYCSOPORTOK (VV, EE)
        # példád:
        # VV 19,000 19,000 19,000
        # EE 20,000 19,000 1,000 ...
        # A legstabilabb: első 3 számot vesszük
        # =========================
        axle_groups = []
        for g, a, b, c in re.findall(r"\n(VV|EE)\s+([0-9]+,[0-9]+)\s+([0-9]+,[0-9]+)\s+([0-9]+,[0-9]+)", text):
            axle_groups.append({
                "group": g,
                "v1_t": a,
                "v2_t": b,
                "v3_t": c
            })

        # =========================
        # 8) ÚTVONAL SZAKASZOK + KM-SZELVÉNYEK
        # Szakaszok: M1, M5, M43...
        # Km: "M1 km 23+500" jelleg
        # =========================
        routes = sorted(set(re.findall(r"\bM\d+\b", text)))
        km_sections = [{"road": r1, "km": km} for (r1, km) in re.findall(r"\b(M\d+)\s*km\s*(\d+\+\d+)\b", text, flags=re.IGNORECASE)]

        # =========================
        # VÁLASZ
        # =========================
        return jsonify({
            "permit_number": permit_number,
            "issue_date": issue_date,
            "from_place": from_place,
            "to_place": to_place,
            "license_plate": license_plate,
            "axle_count": axle_count,
            "weight_t": weight,
            "axles": axles,
            "axle_groups": axle_groups,
            "routes": routes,
            "km_sections": km_sections,
            "raw_text_preview": text[:2000]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if name == "main":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
