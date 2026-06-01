"""Create door and window openings in walls using boolean modifiers."""
from __future__ import annotations
import bpy


def create_opening(opening: dict, wall_objects: dict[str, bpy.types.Object]):
    """Cut a door/window opening into a wall."""
    wall_obj = wall_objects.get(opening.get("wall_id", ""))
    if not wall_obj:
        return
    w = opening["width"] / 1000.0
    h = opening.get("height", 2100) / 1000.0
    pos = opening.get("position", 0) / 1000.0
    wall_loc = wall_obj.location
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(wall_loc.x + pos, wall_loc.y, h / 2))
    cutter = bpy.context.active_object
    cutter.name = f"cutter_{opening.get('id', 'opening')}"
    cutter.scale = (w / 2, wall_obj.scale.y * 2, h / 2)
    cutter.hide_render = True
    mod = wall_obj.modifiers.new(
        name=f"opening_{opening.get('id', 'opening')}", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter


def build_openings(rooms: list[dict]):
    """Create all openings by cutting into walls."""
    wall_objs: dict[str, bpy.types.Object] = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name.startswith('w_'):
            wall_objs[obj.name] = obj
    for room in rooms:
        for opening in room.get("openings", []):
            create_opening(opening, wall_objs)
