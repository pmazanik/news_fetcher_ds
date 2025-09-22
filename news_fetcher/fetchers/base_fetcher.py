from abc import ABC, abstractmethod
import requests
from newspaper import Article
from typing import List, Dict
import logging
from ..config import USER_AGENT

class BaseNewsFetcher(ABC):
    def __init__(self, source_name: str, base_url: str, rss_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.rss_url = rss_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT
        })
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def fetch_article_urls(self, max_articles: int = 20) -> List[str]:
        """Fetch article URLs from the news source"""
        pass

    def fetch_article_content(self, url: str) -> Dict:
        """Fetch full article content using newspaper3k"""
        try:
            article = Article(url)
            article.download()
            article.parse()

            return {
                'title': article.title,
                'text': article.text,
                'publish_date': article.publish_date,
                'authors': article.authors,
                'url': url,
                'source': self.source_name,
                'summary': article.summary if hasattr(article, 'summary') else '',
                'images': list(article.images) if hasattr(article, 'images') else []
            }
        except Exception as e:
            self.logger.error(f"Error fetching article {url}: {e}")
            return None

    def fetch_news(self, max_articles: int = 20) -> List[Dict]:
        """Main method to fetch news articles"""
        self.logger.info(f"Fetching {max_articles} articles from {self.source_name}")

        urls = self.fetch_article_urls(max_articles)
        articles = []

        for url in urls:
            if len(articles) >= max_articles:
                break

            article_data = self.fetch_article_content(url)
            if article_data and article_data.get('text'):
                articles.append(article_data)
                self.logger.info(f"Fetched: {article_data['title'][:50]}...")

        return articles
