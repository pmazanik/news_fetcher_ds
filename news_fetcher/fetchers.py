#!/usr/bin/env python3
"""
News fetchers with enhanced configuration
"""

import feedparser
from typing import List
import logging

import re
from bs4 import BeautifulSoup

from .config import USER_AGENTS, TIMEOUT, MAX_ARTICLES_PER_SOURCE
from .utils import create_session, get_random_user_agent, respectful_delay

class BaseNewsFetcher:
    def __init__(self, source_name: str, base_url: str, rss_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.rss_url = rss_url
        self.session = create_session()
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch_article_urls(self, max_articles: int = None) -> List[str]:
        """Fetch article URLs from RSS feed"""
        max_articles = max_articles or MAX_ARTICLES_PER_SOURCE
        raise NotImplementedError("Subclasses must implement this method")

    def fetch_news(self, max_articles: int = None) -> List[dict]:
        """Main method to fetch news articles"""
        max_articles = max_articles or MAX_ARTICLES_PER_SOURCE
        self.logger.info(f"Fetching {max_articles} articles from {self.source_name}")

        urls = self.fetch_article_urls(max_articles)
        articles = []

        for i, url in enumerate(urls):
            if len(articles) >= max_articles:
                break

            self.logger.info(f"Processing {self.source_name} article {i+1}/{len(urls)}")
            article_data = self.fetch_article_content(url)
            if article_data:
                articles.append(article_data)
                self.logger.info(f"✓ {self.source_name}: '{article_data['title'][:50]}...'")

            respectful_delay()

        return articles

    def fetch_article_content(self, url: str) -> dict:
        """Fetch full article content"""
        from .utils import fetch_article_content
        return fetch_article_content(url, self.source_name)

class BBCFetcher(BaseNewsFetcher):
    def fetch_article_urls(self, max_articles: int = 20) -> List[str]:
        """Fetch BBC article URLs from RSS feed"""
        try:
            feed = feedparser.parse(self.rss_url)
            urls = [entry.link for entry in feed.entries[:max_articles*2] if hasattr(entry, 'link')]
            self.logger.info(f"Found {len(urls)} BBC URLs from RSS")
            return urls
        except Exception as e:
            self.logger.error(f"Error fetching BBC URLs: {e}")
            return []

class NPRFetcher(BaseNewsFetcher):
    def fetch_article_urls(self, max_articles: int = 20) -> List[str]:
        """Fetch NPR article URLs - very reliable RSS"""
        try:
            feed = feedparser.parse(self.rss_url)
            urls = [entry.link for entry in feed.entries[:max_articles*2] if hasattr(entry, 'link')]
            self.logger.info(f"Found {len(urls)} NPR URLs from RSS")
            return urls
        except Exception as e:
            self.logger.error(f"Error fetching NPR URLs: {e}")
            return []

class GuardianFetcher(BaseNewsFetcher):
    def fetch_article_urls(self, max_articles: int = 20) -> List[str]:
        """Fetch The Guardian article URLs"""
        try:
            feed = feedparser.parse(self.rss_url)
            urls = [entry.link for entry in feed.entries[:max_articles*2] if hasattr(entry, 'link')]
            self.logger.info(f"Found {len(urls)} Guardian URLs from RSS")
            return urls
        except Exception as e:
            self.logger.error(f"Error fetching Guardian URLs: {e}")
            return []

class APNewsFetcher(BaseNewsFetcher):
    def fetch_article_urls(self, max_articles: int = 20) -> List[str]:
        """Fetch AP News article URLs with multiple fallback strategies"""
        urls = []

        # Strategy 1: Try AP News RSS feed
        try:
            self.logger.info("Trying AP News RSS feed...")
            feed = feedparser.parse(self.rss_url)
            rss_urls = [entry.link for entry in feed.entries[:max_articles*2] if hasattr(entry, 'link')]
            urls.extend(rss_urls)
            self.logger.info(f"Found {len(rss_urls)} URLs from AP News RSS")
        except Exception as e:
            self.logger.warning(f"AP News RSS failed: {e}")

        # Strategy 2: Try AP News direct scraping if RSS didn't work
        if len(urls) < max_articles:
            try:
                self.logger.info("Trying AP News direct website...")
                response = self.session.get("https://apnews.com", timeout=TIMEOUT)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Look for article links - AP News specific patterns
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href and ('/article/' in href or 'apnews.com/article/' in href):
                            if href.startswith('/'):
                                url = f"https://apnews.com{href}"
                            else:
                                url = href
                            if url not in urls and 'apnews.com' in url:
                                urls.append(url)
                                if len(urls) >= max_articles * 2:
                                    break
            except Exception as e:
                self.logger.warning(f"AP News direct scrape failed: {e}")

        # Strategy 3: Try AP News hub pages
        if len(urls) < max_articles:
            ap_hubs = [
                "https://apnews.com/hub/us-news",
                "https://apnews.com/hub/world-news",
                "https://apnews.com/hub/politics"
            ]

            for hub in ap_hubs:
                if len(urls) >= max_articles * 2:
                    break

                try:
                    self.logger.info(f"Trying AP News hub: {hub}")
                    response = self.session.get(hub, timeout=TIMEOUT)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')

                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if href and ('/article/' in href or 'apnews.com/article/' in href):
                                if href.startswith('/'):
                                    url = f"https://apnews.com{href}"
                                else:
                                    url = href
                                if url not in urls and 'apnews.com' in url:
                                    urls.append(url)
                                    if len(urls) >= max_articles * 2:
                                        break
                except Exception as e:
                    self.logger.warning(f"AP News hub {hub} failed: {e}")
                    continue

        self.logger.info(f"Total AP News URLs found: {len(urls)}")
        return list(set(urls))[:max_articles * 2]

def get_fetcher(source_name: str, base_url: str, rss_url: str):
    """Factory function to get appropriate fetcher"""
    fetchers = {
        "BBC": BBCFetcher,
        "NPR": NPRFetcher,
        "The Guardian": GuardianFetcher,
        "AP News": APNewsFetcher
    }

    fetcher_class = fetchers.get(source_name)
    if fetcher_class:
        return fetcher_class(source_name, base_url, rss_url)
    return None
