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


def _parse_vision_mode(pdf_path: str, project_name: str, backend: str = "auto") -> dict:
    """Vision-enhanced parsing: text base + vision enhancement, with fallback."""
    from src.parser.vision import enhance_with_vision, detect_backend

    # First, do text-based parsing (always works)
    base_model = _parse_text_mode(pdf_path, project_name)

    # Then try to enhance with vision
    if backend == "auto":
        detected_backend, _ = detect_backend()
        backend = detected_backend

    if backend == "none":
        return base_model  # Return text-only results

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        enhanced = enhance_with_vision(
            pdf_path,
            base_model,
            backend=backend,
            api_key=api_key,
        )
        return enhanced
    except Exception as e:
        print(f"Vision enhancement failed: {e}, returning text-only results")
        return base_model


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
    vision_backend = request.args.get("backend", "auto")
    project_name = Path(f.filename).stem

    try:
        pdf_bytes = f.read()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        if mode == "vision":
            model = _parse_vision_mode(tmp_path, project_name, backend=vision_backend)
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
    """Check available backends."""
    from src.parser.vision import detect_backend
    backend_name, model_name = detect_backend()
    return jsonify({
        "status": "ok",
        "vision_available": backend_name != "none",
        "backend": backend_name,
        "model": model_name,
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
