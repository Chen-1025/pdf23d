"""Tests for schema validation."""
from src.schema import validate_project, load_project


def test_validate_empty():
    assert len(validate_project({})) > 0


def test_validate_missing_rooms():
    assert len(validate_project({"rooms": []})) > 0


def test_validate_valid(sample_project):
    assert validate_project(sample_project) == []


def test_validate_invalid_wall(sample_project):
    sample_project["rooms"][0]["walls"].append({"id": "bad"})
    errs = validate_project(sample_project)
    assert any("length" in e for e in errs)
