@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Nincs fájl feltöltve"}), 400

    file = request.files["file"]

    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    lines = text.split("\n")

    # ===== 1️⃣ FEJLÉC / ENGEDÉLY BLOKK =====
    header_block = []
    for line in lines[:80]:   # az eleje szinte mindig a fejléc
        header_block.append(line)

    # ===== 2️⃣ ÚTVONAL BLOKK =====
    route_block = []
    capture = False
    for line in lines:
        if "Útvonal" in line or "útvonal" in line:
            capture = True
        if capture:
            route_block.append(line)
        if capture and len(route_block) > 25:
            break

    # ===== 3️⃣ TENGELYADATOK BLOKK =====
    axle_block = []
    capture = False
    for line in lines:
        if "Tengelyadat" in line or "Tengely-" in line:
            capture = True
        if capture:
            axle_block.append(line)
        if capture and len(axle_block) > 40:
            break

    return jsonify({
        "HEADER_RAW": header_block,
        "ROUTE_RAW": route_block,
        "AXLE_RAW": axle_block
    })
