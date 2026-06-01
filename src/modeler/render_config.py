"""Camera placement and render settings."""
from __future__ import annotations
import math
import bpy


def add_cameras(rooms: list[dict]):
    """Add perspective camera with good overview angle."""
    bpy.ops.object.camera_add(location=(8, -6, 6))
    cam = bpy.context.active_object
    cam.name = "Camera_Perspective"
    cam.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.context.scene.camera = cam


def setup_render(output_dir: str):
    """Configure Cycles render settings."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = f"{output_dir}/render.png"
    scene.eevee.taa_render_samples = 64


def render_and_export(output_dir: str):
    """Render the scene and export GLTF + OBJ."""
    bpy.ops.render.render(write_still=True)
    bpy.ops.export_scene.gltf(
        filepath=f"{output_dir}/model.gltf",
        export_format='GLTF_SEPARATE',
        export_apply=True,
    )
    # OBJ export requires the addon to be enabled in Blender 5.x
    try:
        bpy.ops.wm.obj_export(
            filepath=f"{output_dir}/model.obj",
            export_materials=True,
        )
    except (AttributeError, RuntimeError):
        try:
            bpy.ops.export_scene.obj(
                filepath=f"{output_dir}/model.obj",
                use_materials=True,
            )
        except (AttributeError, RuntimeError):
            print("Warning: OBJ export not available (addon not enabled)")
