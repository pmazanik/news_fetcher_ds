import re
from news_fetcher import canonicalize_url, sha256

def test_canonicalize_url_basic():
    assert canonicalize_url("http://example.com/path/") == "https://example.com/path"
    assert canonicalize_url("https://example.com/path/?a=1&b=2") == "https://example.com/path"
    assert canonicalize_url(" https://example.com/path// ") == "https://example.com/path"

def test_sha256_changes_when_input_changes():
    h1 = sha256("A", "B")
    h2 = sha256("A", "C")
    assert h1 != h2
    assert re.fullmatch(r"[0-9a-f]{64}", h1)

