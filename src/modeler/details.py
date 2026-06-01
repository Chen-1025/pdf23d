"""Add detail decorations: skirting boards, handles, light fixtures."""
from __future__ import annotations
import math
import bpy


def add_skirting(room: dict, height: float = 80.0):
    """Add skirting boards along walls."""
    for wall in room.get("walls", []):
        length = wall["length"]
        thickness = wall.get("thickness", 120)
        start = wall["start"]
        end = wall["end"]
        skirting_h = height / 1000.0
        skirting_d = (thickness + 10) / 1000.0
        length_m = length / 1000.0
        cx = (start[0] + end[0]) / 2000.0
        cy = (start[1] + end[1]) / 2000.0
        dx = (end[0] - start[0]) / 1000.0
        dy = (end[1] - start[1]) / 1000.0
        angle = math.atan2(dy, dx)
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(cx, cy, skirting_h / 2))
        obj = bpy.context.active_object
        obj.name = f"{wall.get('id', 'wall')}_skirting"
        obj.scale = (length_m / 2, skirting_d / 2, skirting_h / 2)
        obj.rotation_euler[2] = angle


def build_details(rooms: list[dict]):
    """Add decorative details to all rooms."""
    for room in rooms:
        add_skirting(room)
