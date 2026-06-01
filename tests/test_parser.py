"""Tests for PDF parser."""
from pathlib import Path
from src.parser.reader import read_pdf
from src.parser.classifier import classify_line, LineType
from src.parser.assembler import match_dimensions, assemble_rooms


def test_read_pdf_extracts_pages():
    pdf_path = Path("data/input/观澜北苑30-1101.pdf")
    if not pdf_path.exists():
        import pytest
        pytest.skip("PDF not available")
    pages = read_pdf(str(pdf_path))
    assert len(pages) >= 1
    for page in pages:
        assert "drawings" in page
        assert "text_blocks" in page
        assert "page_num" in page
        assert page["width"] > 0
        assert page["height"] > 0


def test_classify_short_line_is_dimension():
    seg = {"type": "line", "start": [100, 200], "end": [120, 200]}
    assert classify_line(seg) == LineType.dimension


def test_classify_long_line_is_wall():
    seg = {"type": "line", "start": [0, 0], "end": [5000, 0]}
    assert classify_line(seg) == LineType.wall


def test_match_dimensions_finds_numbers():
    segments = [
        {"type": "line", "start": [100, 200], "end": [500, 200]},
    ]
    texts = [
        {"text": "420", "bbox": [250, 190, 290, 210]},
    ]
    result = match_dimensions(segments, texts)
    assert len(result) == 1
    assert result[0]["dimensions"][0]["value"] == 420


def test_assemble_rooms_creates_structure():
    pages = [{
        "page_num": 0,
        "drawings": [{"segments": [
            {"type": "line", "start": [0, 0], "end": [4200, 0]},
            {"type": "line", "start": [4200, 0], "end": [4200, 3000]},
        ]}],
        "text_blocks": [
            {"text": "4200", "bbox": [1900, -20, 2300, 10]},
            {"text": "30-1101", "bbox": [500, 100, 600, 120]},
        ],
        "width": 5000, "height": 4000,
    }]
    result = assemble_rooms(pages)
    assert "rooms" in result
    assert len(result["rooms"]) > 0
