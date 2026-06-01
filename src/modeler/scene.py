"""Blender scene setup: clear, units, lighting."""
from __future__ import annotations
import bpy
import math


def clear_scene():
    """Remove all objects from the default scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)


def setup_units():
    """Set scene units to millimeters."""
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 0.001


def add_lighting():
    """Add basic 3-point lighting."""
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 8))
    sun = bpy.context.active_object
    sun.data.energy = 5
    sun.rotation_euler = (math.radians(45), math.radians(30), math.radians(45))
    bpy.ops.object.light_add(type='AREA', location=(-3, 0, 4))
    fill = bpy.context.active_object
    fill.data.energy = 200
    fill.data.size = 3


def setup_scene():
    """Initialize the Blender scene for architectural modeling."""
    clear_scene()
    setup_units()
    add_lighting()
