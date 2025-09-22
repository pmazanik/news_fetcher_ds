import feedparser
from typing import List
from .base_fetcher import BaseNewsFetcher

class CNNFetcher(BaseNewsFetcher):
    def fetch_article_urls(self, max_articles: int = 20) -> List[str]:
        """Fetch CNN article URLs from RSS feed"""
        try:
            feed = feedparser.parse(self.rss_url)
            urls = []
            
            for entry in feed.entries[:max_articles]:
                if hasattr(entry, 'link'):
                    urls.append(entry.link)
            
            return urls
        except Exception as e:
            self.logger.error(f"Error fetching CNN URLs: {e}")
            return []
