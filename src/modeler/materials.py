"""Create and assign PBR materials."""
from __future__ import annotations
import bpy


def create_material(name: str, color: tuple[float, float, float, float],
                    roughness: float = 0.5) -> bpy.types.Material:
    """Create a simple PBR material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


MATERIAL_PRESETS = {
    "wall_default": {"color": (0.95, 0.95, 0.93, 1.0), "roughness": 0.9},
    "floor_wood": {"color": (0.55, 0.35, 0.18, 1.0), "roughness": 0.4},
    "floor_tile": {"color": (0.85, 0.83, 0.80, 1.0), "roughness": 0.3},
    "PET/40": {"color": (0.92, 0.90, 0.88, 1.0), "roughness": 0.2},
    "PET/9": {"color": (0.90, 0.88, 0.86, 1.0), "roughness": 0.15},
    "wood_cabinet": {"color": (0.50, 0.30, 0.15, 1.0), "roughness": 0.35},
}


def assign_material(obj: bpy.types.Object, material_name: str):
    """Assign a material to an object, creating it if needed."""
    if material_name not in bpy.data.materials:
        preset = MATERIAL_PRESETS.get(
            material_name,
            {"color": (0.8, 0.8, 0.8, 1.0), "roughness": 0.5},
        )
        create_material(material_name, preset["color"], preset["roughness"])
    if obj.data.materials:
        obj.data.materials[0] = bpy.data.materials[material_name]
    else:
        obj.data.materials.append(bpy.data.materials[material_name])


def apply_materials(rooms: list[dict]):
    """Apply materials to all generated objects based on room data."""
    for obj in bpy.data.objects:
        if obj.name.endswith("_floor"):
            room_name = obj.name.replace("_floor", "")
            for room in rooms:
                if room.get("name") == room_name:
                    floor_mat = room.get("floor", {}).get("material", "floor_wood")
                    assign_material(obj, floor_mat)
                    break
        elif obj.name.startswith("w_"):
            assign_material(obj, "wall_default")
        elif obj.type == 'MESH' and not obj.name.startswith("cutter_"):
            if obj.get("cabinet_material"):
                assign_material(obj, str(obj["cabinet_material"]))
            elif obj.name.endswith("_skirting"):
                assign_material(obj, "wall_default")
