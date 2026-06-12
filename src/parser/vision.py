"""Vision-based PDF analysis with automatic fallback to text mode.

Supports Ollama (free) and Claude (paid) vision backends.
If vision parsing fails on any page, falls back to text-based extraction
for that page, ensuring robustness.
"""
from __future__ import annotations
import base64
import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

import fitz

SYSTEM_PROMPT = """Analyze this cabinet design drawing. Return a single line with
pipe separators. No markdown, no code fences, no explanation. The line:

TYPE|ROOM|FURNITURE|WIDTH|HEIGHT|DEPTH|DIMS|MATERIAL

Where TYPE=elevation/cabinet_detail/floor_plan, ROOM is Chinese room name,
FURNITURE is English type, WIDTH/HEIGHT/DEPTH are mm integers,
DIMS is comma-separated dimension numbers found, MATERIAL is material name.
Example output line:
elevation|厨房|kitchen_cabinet|3000|2500|600|1320,830,420|PET"""  # noqa: E501


def render_page_to_image(page: fitz.Page, scale: float = 1.5) -> bytes:
    return page.get_pixmap(dpi=int(72 * scale)).tobytes("png")


def _check_ollama() -> str | None:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        models = [m["name"] for m in data.get("models", [])]
        for preferred in ["llava-phi3", "minicpm-v", "llava:13b",
                          "llava:7b", "llama3.2-vision", "bakllava"]:
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
    ollama_model = _check_ollama()
    if ollama_model:
        return ("ollama", ollama_model)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return ("claude", "claude-sonnet-4-6")
    return ("none", "")


def _call_ollama_vision(page_num: int, img_bytes: bytes, model: str) -> dict | None:
    """Call Ollama for one page. Returns parsed dict or None on failure."""
    b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": f"Page {page_num}. Pipe-delimited line:",
        "images": [b64],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200},
    }

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    Vision error: {e}")
        return None

    return _parse_pipe_response(result.get("response", ""), page_num)


def _call_claude_vision(page_num: int, img_bytes: bytes, api_key: str = "") -> dict | None:
    """Call Claude for one page. Returns parsed dict or None on failure."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 256,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text": f"Page {page_num}. Pipe-delimited line:"},
        ]}],
    }

    try:
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    Claude error: {e}")
        return None

    text = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return _parse_pipe_response(text, page_num)


def _parse_pipe_response(text: str, page_num: int) -> dict | None:
    """Parse pipe-delimited response. Returns dict or None."""
    text = text.strip()
    # Find the line containing pipe separators
    for line in text.split("\n"):
        line = line.strip()
        # Skip markdown fences, code blocks, SQL, headers
        if line.startswith("```") or line.startswith("#"):
            continue
        if line.startswith("SELECT") or line.startswith("TYPE|"):
            continue
        if "|" in line and not re.match(r'^[\d,]+$', line):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                break
    else:
        return None

    try:
        width = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        height = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
        depth = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0

        # Parse dimension list
        dim_values = []
        if len(parts) > 6:
            for m in re.finditer(r'\d{2,4}', parts[6]):
                dim_values.append(int(m.group()))

        return {
            "page_num": page_num,
            "page_type": parts[0] if parts[0] and parts[0] not in ("1",) else "cabinet_detail",
            "room_name": parts[1] if len(parts) > 1 and parts[1] else "房间",
            "furniture_type": parts[2] if len(parts) > 2 and parts[2] else "cabinet",
            "overall_width_mm": width or 3000,
            "overall_height_mm": height or 2600,
            "overall_depth_mm": depth or 400,
            "dimensions": dim_values,
            "material": parts[7] if len(parts) > 7 else "",
            "notes": "",
        }
    except (ValueError, IndexError) as e:
        print(f"    Parse error: {e} for: {text[:100]}")
        return None


def enhance_with_vision(
    pdf_path: str | Path,
    base_model: dict[str, Any],
    backend: str = "auto",
    model: str = "",
    api_key: str = "",
    progress_callback=None,
) -> dict[str, Any]:
    """Enhance a text-parsed model with vision data.

    For each page, try vision analysis. If successful, use the
    vision-detected dimensions. If not, keep the text-parsed data.

    Args:
        pdf_path: Path to PDF file
        base_model: Model from text-based parser (already has room/cabinet structure)
        backend: "auto", "ollama", or "claude"
        model: Model name override
        api_key: Claude API key
        progress_callback: Optional callback(page, total)

    Returns:
        Enhanced room model dict
    """
    if backend == "auto":
        backend, detected_model = detect_backend()
        model = model or detected_model

    if backend == "none":
        print("  No vision backend, using text-only results")
        return base_model

    print(f"  Enhancing with vision: {backend}/{model}")

    doc = fitz.open(str(pdf_path))
    total_pages = min(len(doc), 13)

    # Build page-to-cabinet mapping from base model
    vision_pages = []

    for i in range(total_pages):
        if progress_callback:
            progress_callback(i + 1, total_pages)

        page = doc[i]
        img_bytes = render_page_to_image(page, scale=1.5)
        page_num = i + 1

        # Call vision
        if backend == "ollama":
            result = _call_ollama_vision(page_num, img_bytes, model)
        else:
            result = _call_claude_vision(page_num, img_bytes, api_key)

        if result:
            vision_pages.append(result)
            print(f"    P{page_num}: vision OK ({result.get('room_name','?')}, "
                  f"w={result.get('overall_width_mm')}, dims={len(result.get('dimensions',[]))})")
        else:
            print(f"    P{page_num}: vision skipped")

        time.sleep(0.3)  # gentle rate limit

    doc.close()

    if progress_callback:
        progress_callback(total_pages, total_pages)

    # Merge vision results into base model
    if vision_pages:
        return _merge_vision_results(base_model, vision_pages)
    return base_model


def _merge_vision_results(
    base_model: dict,
    vision_pages: list[dict],
) -> dict:
    """Merge vision-detected data into the base text-parsed model."""
    rooms = base_model.get("rooms", [])
    if not rooms or not vision_pages:
        return base_model

    # Map vision pages to rooms based on room_name
    for vp in vision_pages:
        v_room = vp.get("room_name", "")
        # Find matching room
        for room in rooms:
            if room["name"] == v_room:
                # Add/update cabinet from vision data
                cab = {
                    "id": f"vision_{vp['page_num']}",
                    "type": vp.get("furniture_type", "cabinet"),
                    "width": vp.get("overall_width_mm", 1000),
                    "height": vp.get("overall_height_mm", 2600),
                    "depth": vp.get("overall_depth_mm", 400),
                    "position": [0, 0],
                    "material": vp.get("material", ""),
                    "source_page": vp["page_num"],
                }
                room.setdefault("cabinets", []).append(cab)
                break

    return base_model
