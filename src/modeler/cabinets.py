"""Generate cabinet/furniture meshes."""
from __future__ import annotations
import bpy


def create_cabinet(cabinet: dict):
    """Create a cabinet as box with shelves and doors."""
    w = cabinet["width"] / 1000.0
    h = cabinet["height"] / 1000.0
    d = cabinet["depth"] / 1000.0
    pos = cabinet.get("position", [0, 0])
    px = pos[0] / 1000.0
    py = pos[1] / 1000.0
    cab_id = cabinet.get("id", "cabinet")
    # Main body
    bpy.ops.mesh.primitive_cube_add(size=1, location=(px + w / 2, py + d / 2, h / 2))
    body = bpy.context.active_object
    body.name = cab_id
    body.scale = (w / 2, d / 2, h / 2)
    body["cabinet_type"] = cabinet.get("type", "generic")
    body["cabinet_material"] = cabinet.get("material", "default")
    # Shelves
    num_shelves = 3
    shelf_thickness = 0.018
    for i in range(1, num_shelves + 1):
        z = h * i / (num_shelves + 1)
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(px + w / 2, py + d / 2, z))
        shelf = bpy.context.active_object
        shelf.name = f"{cab_id}_shelf_{i}"
        shelf.scale = (w / 2 - 0.01, d / 2 - 0.01, shelf_thickness / 2)
    # Doors
    door_gap = 0.003
    for i in range(2):
        door_x = px + w * (i + 0.5) / 2
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(door_x, py + d / 2 + 0.003, h / 2))
        door = bpy.context.active_object
        door.name = f"{cab_id}_door_{i}"
        door.scale = ((w / 2 - door_gap) / 2, 0.004, h / 2 - 0.01)
    return body


def build_cabinets(rooms: list[dict]):
    """Create all cabinets across all rooms."""
    for room in rooms:
        for cab in room.get("cabinets", []):
            create_cabinet(cab)
