import feedparser
from typing import List
from datetime import datetime
from strategies.base_strategy import BaseNewsStrategy
from models.news_article import NewsArticle
import asyncio
from newspaper import Article, ArticleException
import aiohttp

class RSSStrategy(BaseNewsStrategy):
    async def fetch_articles(self, max_articles: int = 20) -> List[NewsArticle]:
        articles = []
        
        try:
            # Parse RSS feed
            feed = feedparser.parse(self.config['url'])
            
            if not feed.entries:
                print(f"No entries found in RSS feed: {self.config['url']}")
                return articles
            
            for entry in feed.entries[:max_articles]:
                try:
                    title = entry.get('title', 'No Title')
                    url = entry.get('link', '')
                    
                    if not url:
                        continue
                    
                    published_date = self._parse_date(entry)
                    
                    # Fetch full content using newspaper3k
                    content = await self._fetch_full_content(url)
                    
                    if not content:
                        content = entry.get('summary', entry.get('description', ''))
                    
                    # Ensure we have some content
                    if not content.strip():
                        content = f"Title: {title}. Source: {self.config['name']}"
                    
                    article = NewsArticle(
                        source=self.config['name'],
                        title=title,
                        content=content,
                        url=url,
                        published_date=published_date,
                        category=self.config.get('category', 'general'),
                        summary=entry.get('summary', '')[:200] + '...' if entry.get('summary') else None
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    print(f"Error processing RSS entry: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching RSS feed {self.config['url']}: {str(e)}")
        
        return articles
    
    def _parse_date(self, entry) -> datetime:
        """Parse various date formats from RSS feeds"""
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    return datetime(*getattr(entry, field)[:6])
                except (TypeError, ValueError):
                    continue
        
        return datetime.now()
    
    async def _fetch_full_content(self, url: str) -> str:
        """Fetch full article content using newspaper3k"""
        try:
            # For async compatibility, we'll use a thread pool
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, self._extract_with_newspaper, url)
            return content
        except Exception as e:
            print(f"Error extracting content with newspaper3k: {str(e)}")
            return ""
    
    def _extract_with_newspaper(self, url: str) -> str:
        """Extract article content using newspaper3k (sync)"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            return article.text
        except ArticleException as e:
            print(f"Newspaper3k error for {url}: {str(e)}")
            return ""
        except Exception as e:
            print(f"Unexpected error in newspaper3k for {url}: {str(e)}")
            return ""