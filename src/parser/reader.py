"""Read PDF pages and extract raw data with proper encoding."""
from __future__ import annotations
from typing import Any


def read_pdf(path: str) -> list[dict[str, Any]]:
    """Extract drawings and text blocks from each page of a PDF."""
    import fitz
    doc = fitz.open(path)
    pages: list[dict[str, Any]] = []
    for i in range(len(doc)):
        page = doc[i]
        # Text blocks with positions
        text_blocks = []
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line.get("spans", []))
                    text = text.strip()
                    if text:
                        text_blocks.append({
                            "text": text,
                            "bbox": list(line["bbox"]),
                        })
        # Drawings (vector paths)
        drawings = []
        for d in page.get_drawings():
            segments = []
            for item in d.get("items", []):
                if item[0] == "l":
                    segments.append({
                        "type": "line",
                        "start": [item[1].x, item[1].y],
                        "end": [item[2].x, item[2].y],
                    })
                elif item[0] == "re":
                    rect = item[1]
                    segments.append({
                        "type": "rect",
                        "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    })
            if segments:
                drawings.append({
                    "segments": segments,
                    "rect": [d["rect"].x0, d["rect"].y0, d["rect"].x1, d["rect"].y1],
                })
        pages.append({
            "page_num": i,
            "drawings": drawings,
            "text_blocks": text_blocks,
            "width": page.rect.width,
            "height": page.rect.height,
            "plain_text": page.get_text("text"),
        })
    doc.close()
    return pages
