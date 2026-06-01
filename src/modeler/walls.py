"""Generate wall meshes and floors from room data."""
from __future__ import annotations
import math
import bpy


def create_wall(wall: dict):
    """Create a single wall as a scaled cube."""
    length = wall["length"] / 1000.0
    height = wall["height"] / 1000.0
    thickness = wall.get("thickness", 120) / 1000.0
    start = [wall["start"][0] / 1000.0, wall["start"][1] / 1000.0]
    end = [wall["end"][0] / 1000.0, wall["end"][1] / 1000.0]
    cx = (start[0] + end[0]) / 2
    cy = (start[1] + end[1]) / 2
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, height / 2))
    wall_obj = bpy.context.active_object
    wall_obj.name = wall.get("id", "wall")
    wall_obj.scale = (length / 2, thickness / 2, height / 2)
    wall_obj.rotation_euler[2] = angle
    return wall_obj


def create_floor(room: dict):
    """Create floor plane for a room."""
    floor = room.get("floor", {})
    width = floor.get("width", 4000) / 1000.0
    depth = floor.get("depth", 3000) / 1000.0
    bpy.ops.mesh.primitive_plane_add(size=1, location=(width / 2, depth / 2, 0))
    floor_obj = bpy.context.active_object
    floor_obj.name = f"{room.get('name', 'room')}_floor"
    floor_obj.scale = (width / 2, depth / 2, 1)
    return floor_obj


def build_walls_and_floors(rooms: list[dict]):
    """Create walls and floors for all rooms."""
    for room in rooms:
        create_floor(room)
        for wall in room.get("walls", []):
            create_wall(wall)
