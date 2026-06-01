"""Real-time PDF-to-3D web application."""
from __future__ import annotations
import json
import io
import sys
from pathlib import Path

from flask import Flask, request, jsonify, render_template

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.parser.reader import read_pdf
from src.parser.classifier import classify_page, group_pages
from src.parser.assembler import build_room_model

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB


@app.route("/")
def index():
    return render_template("viewer.html")


@app.route("/api/parse", methods=["POST"])
def api_parse():
    """Accept PDF upload, parse it, return room model JSON."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files supported"}), 400

    try:
        pdf_bytes = f.read()
        # Save to temp file for PyMuPDF
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # Parse
        pages = read_pdf(tmp_path)
        classified = []
        for p in pages:
            info = classify_page(p["text_blocks"], p.get("plain_text", ""))
            classified.append({**p, "classification": info})

        groups = group_pages(classified)
        model = build_room_model(groups, Path(f.filename).stem)

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)

        return jsonify(model)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    print("Starting PDF-to-3D server at http://localhost:5000")
    app.run(debug=True, port=5000)


if __name__ == "__main__":
    main()
