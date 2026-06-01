"""Main Blender modeling entry point.

Usage: blender --background --python build_model.py -- input.json output_dir/
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# Add project root to path so Blender's Python finds our modules
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def main():
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
    else:
        print("Usage: blender --background --python build_model.py -- input.json output_dir/")
        sys.exit(1)
    if len(args) < 2:
        print("Missing input JSON or output dir")
        sys.exit(1)
    input_path = args[0]
    output_dir = args[1]
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(input_path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    rooms = data.get("rooms", [])
    print(f"Building model: {len(rooms)} rooms")
    from src.modeler.scene import setup_scene
    from src.modeler.walls import build_walls_and_floors
    from src.modeler.cabinets import build_cabinets
    from src.modeler.openings import build_openings
    from src.modeler.details import build_details
    from src.modeler.materials import apply_materials
    from src.modeler.render_config import add_cameras, setup_render, render_and_export
    setup_scene()
    print("Scene set up")
    build_walls_and_floors(rooms)
    print("Walls and floors created")
    build_cabinets(rooms)
    print("Cabinets created")
    build_openings(rooms)
    print("Openings cut")
    build_details(rooms)
    print("Details added")
    apply_materials(rooms)
    print("Materials applied")
    add_cameras(rooms)
    setup_render(output_dir)
    print("Rendering...")
    render_and_export(output_dir)
    print(f"Done! Output in {output_dir}")


if __name__ == "__main__":
    main()
