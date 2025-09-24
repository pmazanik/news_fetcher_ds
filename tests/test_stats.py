from news_fetcher import Article, compute_stats

def make_article(source, title="t", description=None, content=None):
    return Article(
        id=title + source,
        source=source,
        url=f"https://example.com/{source}/{title}",
        title=title,
        description=description,
        content=content,
        published_at=None,
        authors=[],
        tags=[],
        language=None,
        content_hash=title + source,
    )

def test_compute_stats_per_source():
    # BBC: two articles
    a1 = make_article("BBC-World", content="word " * 10)         # 10 words
    a2 = make_article("BBC-World", content="x" * 50)             # 50 chars, 1 word
    # AP: one article with only description
    a3 = make_article("AP-Top", description="alpha beta gamma")  # 3 words

    stats = compute_stats([a1, a2, a3])

    assert "BBC-World" in stats and "AP-Top" in stats
    bbc = stats["BBC-World"]
    ap = stats["AP-Top"]

    assert bbc["count"] == 2
    # max words should be 10
    assert bbc["max_words"] >= 10
    # max chars at least 50
    assert bbc["max_chars"] >= 50

    assert ap["count"] == 1
    assert ap["max_words"] == 3
    assert ap["max_chars"] == len("alpha beta gamma")

