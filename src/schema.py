"""Shared JSON schema and validation for the 3D model pipeline."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def validate_project(data: dict[str, Any]) -> list[str]:
    """Validate project JSON structure. Returns list of error messages (empty = valid)."""
    errors: list[str] = []
    if "rooms" not in data:
        errors.append("Missing 'rooms' key")
        return errors
    if not isinstance(data["rooms"], list) or len(data["rooms"]) == 0:
        errors.append("'rooms' must be a non-empty list")
        return errors
    for i, room in enumerate(data["rooms"]):
        prefix = f"rooms[{i}]"
        if "name" not in room:
            errors.append(f"{prefix}: missing 'name'")
        if "walls" in room:
            for j, wall in enumerate(room["walls"]):
                wp = f"{prefix}.walls[{j}]"
                if "length" not in wall:
                    errors.append(f"{wp}: missing 'length'")
        if "cabinets" in room:
            for j, cab in enumerate(room["cabinets"]):
                cp = f"{prefix}.cabinets[{j}]"
                for key in ("width", "height", "depth"):
                    if key not in cab:
                        errors.append(f"{cp}: missing '{key}'")
    return errors


def load_project(path: str | Path) -> dict[str, Any]:
    """Load and validate a project JSON file. Raises ValueError on invalid."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    errs = validate_project(data)
    if errs:
        raise ValueError("\n".join(errs))
    return data
