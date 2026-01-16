from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import os

from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# ======================
# APP INIT
# ======================
app = Flask(__name__)
CORS(app)

# ======================
# DATABASE
# ======================
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
Session = sessionmaker(bind=engine) if engine else None
Base = declarative_base()

class Permit(Base):
    __tablename__ = "permits"
    id = Column(Integer, primary_key=True)
    permit_number = Column(String)
    data = Column(JSON)

if engine:
    Base.metadata.create_all(engine)

# ======================
# HELPERS
# ======================
def find(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None

# ======================
# ROUTES
# ======================
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    try:
        with pdfplumber.open(io.BytesIO(request.files["file"].read())) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # ======================
        # BASIC FIELDS
        # ======================
        permit_number = find(r"(UE-[A-Z]-\d+/\d{4})", text)
        issue_date = find(r"(\d{4}\.\s?\d{2}\.\s?\d{2})", text)

        from_place = find(
            r"10\.\s*Kiindulás.*?\n([A-ZÁÉÍÓÖŐÚÜŰa-z0-9 ,\-]+)", text
        )
        to_place = find(
            r"12\.\s*Célállomás.*?\n([A-ZÁÉÍÓÖŐÚÜŰa-z0-9 ,\-]+)", text
        )

        plates = re.findall(r"\n([A-Z]{2,3}\d{3}\s?[A-Z])\b", text)
        license_plate = ", ".join(plates) if plates else None

        # ======================
        # AXLES
        # ======================
        axles = []
        axle_lines = re.findall(
            r"\n(\d)\s+([AVE])\s+(?:X\s+)?([\d,]+)", text
        )

        for idx, typ, load in axle_lines:
            axles.append({
                "index": int(idx),
                "type": typ,
                "load_t": load
            })

        # ======================
        # AXLE GROUPS (VV, EE)
        # ======================
        axle_groups = []
        group_lines = re.findall(
            r"\n(VV|EE)\s+([\d,]+)\s+([\d,]+)", text
        )

        for group, requested, allowed in group_lines:
            axle_groups.append({
                "group": group,
                "requested_t": requested,
                "allowed_t": allowed
            })

        # ======================
        # ROUTES + KM
        # ======================
        routes = sorted(set(re.findall(r"\bM\d+\b", text)))

        km_sections = re.findall(
            r"(M\d+)\s*km\s*(\d+\+\d+)", text
        )

        km_data = [
            {"road": road, "km": km}
            for road, km in km_sections
        ]

        # ======================
        # FINAL DATA
        # ======================
        result = {
            "permit_number": permit_number,
            "issue_date": issue_date,
            "from_place": from_place,
            "to_place": to_place,
            "license_plate": license_plate,
            "axles": axles,
            "axle_groups": axle_groups,
            "routes": routes,
            "km_sections": km_data
        }

        # ======================
        # SAVE TO DB
        # ======================
        if Session:
            session = Session()
            session.add(Permit(
                permit_number=permit_number,
                data=result
            ))
            session.commit()

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
