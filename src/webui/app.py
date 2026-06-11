"""Real-time PDF-to-3D web application."""
from __future__ import annotations
import json
import os
import sys
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, render_template

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.parser.reader import read_pdf
from src.parser.classifier import classify_page, group_pages
from src.parser.assembler import build_room_model

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


@app.route("/")
def index():
    return render_template("viewer.html")


def _parse_text_mode(pdf_path: str, project_name: str) -> dict:
    """Original text-based parsing pipeline."""
    pages = read_pdf(pdf_path)
    classified = []
    for p in pages:
        info = classify_page(p["text_blocks"], p.get("plain_text", ""))
        classified.append({**p, "classification": info})
    groups = group_pages(classified)
    return build_room_model(groups, project_name)


def _parse_vision_mode(pdf_path: str, project_name: str) -> dict:
    """Vision model-based parsing pipeline."""
    from src.parser.vision import analyze_pdf_with_vision
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError(
            "Vision mode requires ANTHROPIC_API_KEY environment variable. "
            "Set it via: export ANTHROPIC_API_KEY=your-key-here"
        )
    return analyze_pdf_with_vision(pdf_path, api_key)


@app.route("/api/parse", methods=["POST"])
def api_parse():
    """Parse PDF and return room model JSON.

    Query params:
        mode: "text" (default) or "vision"
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files supported"}), 400

    mode = request.args.get("mode", "text")
    project_name = Path(f.filename).stem

    try:
        pdf_bytes = f.read()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        if mode == "vision":
            model = _parse_vision_mode(tmp_path, project_name)
        else:
            model = _parse_text_mode(tmp_path, project_name)

        Path(tmp_path).unlink(missing_ok=True)
        return jsonify(model)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/health")
def health():
    """Check if vision mode is available."""
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    return jsonify({
        "status": "ok",
        "vision_available": has_key,
    })


def main():
    print("Starting PDF-to-3D server at http://localhost:5000")
    has_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if has_key:
        print("  Vision mode: ENABLED (Claude API)")
    else:
        print("  Vision mode: DISABLED (set ANTHROPIC_API_KEY to enable)")
    app.run(debug=True, port=5000)


if __name__ == "__main__":
    main()
