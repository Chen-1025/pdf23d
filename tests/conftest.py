"""Shared fixtures for tests."""
import pytest


@pytest.fixture
def sample_room() -> dict:
    return {
        "name": "test_room",
        "walls": [
            {"id": "w1", "length": 4000, "height": 2800, "thickness": 120,
             "start": [0, 0], "end": [4000, 0]},
            {"id": "w2", "length": 3000, "height": 2800, "thickness": 120,
             "start": [4000, 0], "end": [4000, 3000]},
        ],
        "floor": {"width": 4000, "depth": 3000, "material": "floor_wood"},
        "cabinets": [
            {"id": "c1", "type": "wardrobe", "width": 2000, "height": 2600,
             "depth": 600, "position": [0, 0], "material": "PET/40"},
        ],
        "openings": [
            {"id": "d1", "type": "door", "width": 900, "height": 2100,
             "position": 2000, "wall_id": "w1"},
        ],
    }


@pytest.fixture
def sample_project(sample_room) -> dict:
    return {"project": "test_project", "rooms": [sample_room]}
