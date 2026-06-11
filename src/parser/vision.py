"""Vision-based PDF analysis using Claude Vision API.

Renders PDF pages as images and sends them to Claude for
precise dimension and layout extraction.
"""
from __future__ import annotations
import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import fitz

# Claude API endpoint
ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Maximum pages to analyze per request (to control cost/tokens)
MAX_PAGES_PER_BATCH = 3

# System prompt for blueprint analysis
SYSTEM_PROMPT = """You are an architectural blueprint analyzer. Your task is to examine images
of interior design / custom cabinetry drawings and extract precise dimensional data.

For each page image you see, identify:

1. **Page type**: floor_plan, elevation, cabinet_detail, or section
2. **Room/Furniture**: What room or furniture piece is this? (kitchen, living room, bedroom,
   wardrobe, tv_cabinet, entrance_cabinet, study, shelving, etc.)
3. **Overall dimensions**: The total width, height, and depth shown (in millimeters).
   Look for dimension lines with arrowheads or tick marks, and the numbers near them.
4. **Individual segments**: Each labeled dimension on the drawing. Look for:
   - Horizontal dimension lines (text centered between tick marks)
   - Vertical dimension lines
   - Numbers in the format like "420", "830", "2560" (all measurements in mm)
5. **Material notes**: Any material specifications (PET, wood grain, etc.)
6. **Labels**: Any Chinese text labels identifying components

**IMPORTANT RULES:**
- ALL measurements are in MILLIMETERS (mm)
- Dimension numbers are typically 2-4 digits (e.g., 420, 1320, 2560)
- Look carefully at the dimension LINES - they usually have tick marks at ends
- The dimension number is centered between the tick marks
- DO NOT confuse design note text with dimension values
- Report ONLY values that are clearly associated with dimension lines

Output ONLY valid JSON, no markdown, no explanation:
{
  "pages": [
    {
      "page_num": 1,
      "page_type": "floor_plan",
      "room_name": "厨房",
      "furniture_type": "kitchen_cabinet",
      "overall_width_mm": 3000,
      "overall_height_mm": 2500,
      "overall_depth_mm": 600,
      "dimensions": [
        {"label": "w1", "value": 1320, "description": "base cabinet width"},
        {"label": "w2", "value": 830, "description": "wall cabinet width"}
      ],
      "material": "PET matte white",
      "notes": "Base cabinet with aluminum handle-free design"
    }
  ]
}"""


def render_page_to_image(page: fitz.Page, scale: float = 2.0) -> bytes:
    """Render a PDF page to PNG image bytes."""
    pix = page.get_pixmap(dpi=int(72 * scale))
    return pix.tobytes("png")


def encode_image(image_bytes: bytes) -> str:
    """Base64-encode image bytes for API."""
    return base64.b64encode(image_bytes).decode("utf-8")


def call_claude_vision(
    images: list[tuple[int, bytes]],
    api_key: str = "",
) -> dict[str, Any]:
    """Send page images to Claude Vision API for analysis.

    Args:
        images: List of (page_number, png_bytes) tuples
        api_key: Anthropic API key

    Returns:
        Parsed JSON response with page analyses
    """
    import urllib.request
    import urllib.error

    key = api_key or API_KEY
    if not key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Build content blocks
    content_blocks = []

    for page_num, img_bytes in images:
        b64 = encode_image(img_bytes)
        content_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": b64,
            }
        })
        content_blocks.append({
            "type": "text",
            "text": f"(Page {page_num} image above)"
        })

    content_blocks.append({
        "type": "text",
        "text": "Analyze ALL pages above. "
                "For each page, extract precise dimensions from the dimension lines. "
                "Return ONLY valid JSON matching the specified format. "
                "No markdown, no explanation — just the JSON object."
    })

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": content_blocks}
        ],
    }

    req = urllib.request.Request(
        ANTHROPIC_API,
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
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"API error {e.code}: {error_body}")

    # Extract text from response
    text_response = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            text_response += block.get("text", "")

    # Parse JSON from response (strip any markdown wrapping)
    text_response = text_response.strip()
    if text_response.startswith("```"):
        lines = text_response.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text_response = "\n".join(lines)

    try:
        return json.loads(text_response)
    except json.JSONDecodeError:
        # Try to extract JSON block
        import re
        match = re.search(r'\{.*\}', text_response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse JSON from response: {text_response[:500]}")


def analyze_pdf_with_vision(
    pdf_path: str | Path,
    api_key: str = "",
    progress_callback=None,
) -> dict[str, Any]:
    """Analyze a PDF using vision model.

    Args:
        pdf_path: Path to PDF file
        api_key: Anthropic API key
        progress_callback: Optional callback(step, total) for progress

    Returns:
        Structured room model dict
    """
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    all_results = []

    # Process pages in batches
    for batch_start in range(0, total_pages, MAX_PAGES_PER_BATCH):
        batch_end = min(batch_start + MAX_PAGES_PER_BATCH, total_pages)
        batch_images = []

        for i in range(batch_start, batch_end):
            if progress_callback:
                progress_callback(i + 1, total_pages)
            page = doc[i]
            img_bytes = render_page_to_image(page, scale=1.5)
            batch_images.append((i + 1, img_bytes))

        print(f"  Analyzing pages {batch_start+1}-{batch_end} of {total_pages}...")
        result = call_claude_vision(batch_images, api_key)
        pages_data = result.get("pages", [])
        all_results.extend(pages_data)

        # Rate limiting
        if batch_end < total_pages:
            time.sleep(1)

    doc.close()

    if progress_callback:
        progress_callback(total_pages, total_pages)

    # Convert vision results to room model format
    return _vision_results_to_model(all_results)


def _vision_results_to_model(pages_data: list[dict]) -> dict[str, Any]:
    """Convert vision analysis results to the standard room model format."""
    from src.parser.assembler import build_room_model

    # Group pages by room
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
        room_groups[room]["pages"].append({
            "page_num": p.get("page_num", 0),
            "type": p.get("page_type", "cabinet_detail"),
            "furniture_type": p.get("furniture_type", "cabinet"),
            "room_name": room,
            "dimensions": [d["value"] for d in p.get("dimensions", [])],
            "max_dim": max([d["value"] for d in p.get("dimensions", [])]) if p.get("dimensions") else p.get("overall_width_mm", 1000),
            "est_width": p.get("overall_width_mm", 1000),
            "est_height": p.get("overall_height_mm", 2600),
            "est_depth": p.get("overall_depth_mm", 400),
            "material": p.get("material", ""),
            "labels": p.get("notes", "").split("\n") if p.get("notes") else [],
        })

    groups = list(room_groups.values())
    return build_room_model(groups, "vision-analysis")
