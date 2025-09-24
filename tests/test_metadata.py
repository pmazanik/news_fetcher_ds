from vector_db import _sanitize_metadata

def test_sanitize_metadata_converts_lists_and_drops_none():
    meta = {
        "id": "123",
        "source": "BBC",
        "url": "https://example.com",
        "published_at": None,
        "topics": ["A", "B", "C"],
        "score": 1.23,
        "flag": True,
        "extra": {"nested": "x"},
    }
    clean = _sanitize_metadata(meta)
    # None dropped
    assert "published_at" not in clean
    # list joined
    assert clean["topics"] == "A, B, C"
    # scalars preserved
    assert clean["score"] == 1.23
    assert clean["flag"] is True
    # dict stringified
    assert isinstance(clean["extra"], str) and "nested" in clean["extra"]

