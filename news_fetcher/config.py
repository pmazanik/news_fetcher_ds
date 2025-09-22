import os
from dataclasses import dataclass

@dataclass
class NewsSource:
    name: str
    base_url: str
    rss_url: str

# Configuration for news sources - REPLACED CNN with NPR
NEWS_SOURCES = [
    NewsSource(
        name="BBC",
        base_url="https://www.bbc.com",
        rss_url="https://feeds.bbci.co.uk/news/rss.xml"
    ),
    NewsSource(
        name="NPR",  # REPLACED CNN
        base_url="https://www.npr.org",
        rss_url="https://feeds.npr.org/1001/rss.xml"  # NPR News RSS
    ),
    NewsSource(
        name="The Guardian",
        base_url="https://www.theguardian.com",
        rss_url="https://www.theguardian.com/world/rss"
    ),
    NewsSource(
        name="AP News",
        base_url="https://apnews.com",
        rss_url="https://apnews.com/feed"
    )
]

# Multiple user agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

# Output directory
OUTPUT_DIR = "news_data"
MAX_ARTICLES_PER_SOURCE = 20
TIMEOUT = 15
REQUEST_DELAY = (0.5, 1.5)
