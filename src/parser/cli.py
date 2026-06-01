"""CLI: Parse PDF → classify pages → group → build model → save JSON."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from src.parser.reader import read_pdf
from src.parser.classifier import classify_page, group_pages
from src.parser.assembler import build_room_model


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.parser.cli <pdf_path> [output_json]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "data/parsed/output.json"

    print(f"Reading: {pdf_path}")
    pages = read_pdf(pdf_path)
    print(f"  {len(pages)} pages\n")

    # Classify
    classified = []
    for p in pages:
        info = classify_page(p["text_blocks"], p.get("plain_text", ""))
        classified.append({**p, "classification": info})
        c = info
        print(f"  P{p['page_num']+1:2d}: {c['type']:15s} | {c['furniture_type']:18s} | "
              f"room={c['room_name']:4s} | mat={c['material']:14s} | "
              f"max={c['max_dim']:4d}mm")

    # Group
    groups = group_pages(classified)
    print(f"\n=== {len(groups)} rooms ===")
    for g in groups:
        pnums = [f"P{p['page_num']}" for p in g["pages"]]
        n_pieces = len(set(p.get('furniture_type','') for p in g['pages']))
        print(f"  {g['name']} ({g['id']}): {len(g['pages'])} pages, "
              f"{n_pieces} furniture types → {', '.join(pnums)}")

    # Build model
    project_name = Path(pdf_path).stem
    model = build_room_model(groups, project_name)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

    total_cabs = sum(len(r.get("cabinets", [])) for r in model["rooms"])
    print(f"\nModel: {len(model['rooms'])} rooms, {total_cabs} cabinets → {output_path}")
    for r in model["rooms"]:
        cabs = r.get("cabinets", [])
        print(f"  {r['name']}: {r['floor']['width']}×{r['floor']['depth']}mm, "
              f"{len(r['walls'])} walls, {len(cabs)} cabinets")


if __name__ == "__main__":
    main()
