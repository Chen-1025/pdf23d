"""Vision-based PDF analysis supporting multiple backends.

Backends:
  - ollama: Free local vision model (llava, minicpm-v, llama3.2-vision)
  - claude: Anthropic Claude Vision API (paid, high accuracy)

Auto-detects Ollama if running locally. Falls back to Claude if API key set.
"""
from __future__ import annotations
import base64
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

import fitz

MAX_PAGES_PER_BATCH = 3

SYSTEM_PROMPT = """You are an architectural blueprint analyzer. Examine the image of a
cabinet/furniture design drawing and extract precise dimensional data.

Identify:
1. **Page type**: floor_plan, elevation, cabinet_detail, or section
2. **Room name**: (厨房/客厅/卧室/书房/玄关/餐厅/卫生间/阳台/储物间)
3. **Furniture type**: kitchen_cabinet, wardrobe, tv_cabinet, shelving, entrance_cabinet,
   study_furniture, sideboard, storage, bathroom_cabinet, cabinet
4. **Overall dimensions**: total width, height, depth in MILLIMETERS.
   Find dimension lines with tick marks/arrows and read the numbers near them.
5. **Individual dimensions**: Each labeled measurement on the drawing.
   Numbers are 2-4 digits (e.g., 420, 830, 2560). ALL in mm.
6. **Material**: Any PET, wood grain, or material specs visible.
7. **Notes**: Key Chinese labels or design notes.

CRITICAL:
- ALL measurements in millimeters (mm)
- Only report numbers clearly associated with dimension lines
- Do NOT confuse phone numbers or page numbers with dimensions"""  # noqa: E501

OUTPUT_SCHEMA = """{
  "pages": [{
    "page_num": 1,
    "page_type": "elevation",
    "room_name": "厨房",
    "furniture_type": "kitchen_cabinet",
    "overall_width_mm": 3000,
    "overall_height_mm": 2500,
    "overall_depth_mm": 600,
    "dimensions": [
      {"label": "A", "value": 1320, "description": "cabinet width"},
      {"label": "B", "value": 830, "description": "door height"}
    ],
    "material": "PET",
    "notes": "Base cabinet"
  }]
}"""  # noqa: E501


# ── Backend Detection ──

def _check_ollama() -> str | None:
    """Check if Ollama is running and has a vision model."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        models = [m["name"] for m in data.get("models", [])]
        # Prefer vision-capable models in order of quality
        for preferred in ["llava-phi3", "minicpm-v",
                          "llava:13b", "llava:7b", "llama3.2-vision", "bakllava"]:
            for m in models:
                if m.startswith(preferred.split(":")[0]):
                    return m
        for m in models:
            if any(k in m.lower() for k in ["vision", "llava", "minicpm", "bakllava"]):
                return m
        return None
    except Exception:
        return None


def detect_backend() -> tuple[str, str]:
    """Auto-detect available vision backend.

    Returns: (backend_name, model_name)
    """
    # Check Ollama first (free)
    ollama_model = _check_ollama()
    if ollama_model:
        return ("ollama", ollama_model)

    # Check Claude API key
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ("claude", "claude-sonnet-4-6")

    return ("none", "")


# ── Backend Implementations ──

def _call_ollama(model: str, images: list[tuple[int, bytes]]) -> dict[str, Any]:
    """Call Ollama vision API using native /api/chat format."""
    # Ollama expects images as top-level field in message, not in content blocks
    # Process images one at a time for simplicity, or use images array for multi-image
    all_images = [base64.b64encode(img_bytes).decode("utf-8")
                  for _, img_bytes in images]

    page_descs = "\n".join(f"- Page {n}" for n, _ in images)

    prompt = (
        f"I am showing you {len(images)} page(s) from a cabinet design PDF:\n"
        f"{page_descs}\n\n"
        f"Analyze ALL pages and extract precise dimensions.\n"
        f"Output ONLY valid JSON matching this schema, no markdown:\n"
        f"{OUTPUT_SCHEMA}"
    )

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "images": all_images,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 4096},
    }

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"Ollama error {e.code}: {body[:500]}")

    return _parse_response(result.get("response", ""))


def _call_claude(images: list[tuple[int, bytes]], api_key: str = "") -> dict[str, Any]:
    """Call Anthropic Claude Vision API."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    content_blocks = []
    for page_num, img_bytes in images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content_blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": b64}
        })
        content_blocks.append({"type": "text", "text": f"(Page {page_num})"})

    content_blocks.append({
        "type": "text",
        "text": f"Output ONLY valid JSON:\n{OUTPUT_SCHEMA}"
    })

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": content_blocks}],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"Claude API error {e.code}: {body}")

    text = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return _parse_response(text)


def _parse_response(text: str) -> dict[str, Any]:
    """Parse JSON from model response text."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Cannot parse JSON from: {text[:500]}")


# ── Rendering ──

def render_page_to_image(page: fitz.Page, scale: float = 2.0) -> bytes:
    """Render PDF page to PNG bytes."""
    return page.get_pixmap(dpi=int(72 * scale)).tobytes("png")


# ── Main API ──

def analyze_pdf_with_vision(
    pdf_path: str | Path,
    backend: str = "auto",
    model: str = "",
    api_key: str = "",
    progress_callback=None,
) -> dict[str, Any]:
    """Analyze a PDF using a vision model.

    Args:
        pdf_path: Path to PDF file
        backend: "auto", "ollama", or "claude"
        model: Model name override (auto-detected if empty)
        api_key: API key for Claude backend
        progress_callback: Optional callback(page, total)

    Returns:
        Room model dict
    """
    # Resolve backend
    if backend == "auto":
        backend, detected_model = detect_backend()
        model = model or detected_model
    elif backend == "ollama":
        model = model or (_check_ollama() or "llava:13b")
    elif backend == "claude":
        model = model or "claude-sonnet-4-6"

    if backend == "none":
        raise RuntimeError(
            "No vision backend available.\n"
            "Install Ollama: https://ollama.com\n"
            "Then: ollama pull llama3.2-vision:11b\n"
            "Or set ANTHROPIC_API_KEY for Claude."
        )

    print(f"Using vision backend: {backend} ({model})")

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    all_results = []

    for batch_start in range(0, total_pages, MAX_PAGES_PER_BATCH):
        batch_end = min(batch_start + MAX_PAGES_PER_BATCH, total_pages)
        batch_images = []

        for i in range(batch_start, batch_end):
            if progress_callback:
                progress_callback(i + 1, total_pages)
            img_bytes = render_page_to_image(doc[i], scale=1.5)
            batch_images.append((i + 1, img_bytes))

        print(f"  Pages {batch_start+1}-{batch_end} of {total_pages}...")

        if backend == "ollama":
            result = _call_ollama(model, batch_images)
        else:
            result = _call_claude(batch_images, api_key)

        all_results.extend(result.get("pages", []))

        if batch_end < total_pages:
            time.sleep(0.5)

    doc.close()

    if progress_callback:
        progress_callback(total_pages, total_pages)

    return _results_to_model(all_results)


def _results_to_model(pages_data: list[dict]) -> dict[str, Any]:
    """Convert vision results to room model format."""
    from src.parser.assembler import build_room_model

    room_groups: dict[str, dict] = {}
    for p in pages_data:
        room = p.get("room_name", "房间")
        if room not in room_groups:
            room_groups[room] = {
                "id": f"room_{len(room_groups)+1}",
                "name": room,
                "pages": [],
                "material_type": "",
                "project": "",
            }
        dims = [d["value"] for d in p.get("dimensions", [])]
        room_groups[room]["pages"].append({
            "page_num": p.get("page_num", 0),
            "type": p.get("page_type", "cabinet_detail"),
            "furniture_type": p.get("furniture_type", "cabinet"),
            "room_name": room,
            "dimensions": dims,
            "max_dim": max(dims) if dims else p.get("overall_width_mm", 1000),
            "est_width": p.get("overall_width_mm", 1000),
            "est_height": p.get("overall_height_mm", 2600),
            "est_depth": p.get("overall_depth_mm", 400),
            "material": p.get("material", ""),
            "labels": [p.get("notes", "")],
        })

    return build_room_model(list(room_groups.values()), "vision-analysis")
