from typing import List
from strategies.base_strategy import BaseNewsStrategy
from models.news_article import NewsArticle
from bs4 import BeautifulSoup
import aiohttp
from datetime import datetime
import asyncio
from urllib.parse import urljoin

class WebCrawlerStrategy(BaseNewsStrategy):
    async def fetch_articles(self, max_articles: int = 20) -> List[NewsArticle]:
        articles = []
        
        try:
            # Fetch the main page
            html = await self.fetch_url(self.config['url'])
            if not html:
                return articles
            
            soup = BeautifulSoup(html, 'html.parser')
            crawler_config = self.config.get('crawler_config', {})
            
            # Find article links
            article_links = soup.select(crawler_config.get('article_selector', 'a'))
            base_url = crawler_config.get('base_url', self.config['url'])
            
            processed_articles = 0
            for link in article_links:
                if processed_articles >= max_articles:
                    break
                
                try:
                    article_url = link.get('href')
                    if not article_url:
                        continue
                    
                    # Make absolute URL
                    if not article_url.startswith('http'):
                        article_url = urljoin(base_url, article_url)
                    
                    # Fetch and parse individual article
                    article = await self._parse_article_page(article_url)
                    if article and article.content.strip():
                        articles.append(article)
                        processed_articles += 1
                        
                except Exception as e:
                    print(f"Error processing article link: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error in web crawler: {str(e)}")
        
        return articles
    
    async def _parse_article_page(self, url: str) -> NewsArticle:
        """Parse individual article page"""
        try:
            html = await self.fetch_url(url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            crawler_config = self.config.get('crawler_config', {})
            
            # Extract title
            title_elem = soup.select_one(crawler_config.get('title_selector', 'h1'))
            title = title_elem.get_text().strip() if title_elem else "No Title"
            
            # Extract content
            content_selector = crawler_config.get('content_selector', 'p')
            content_elems = soup.select(content_selector)
            content = ' '.join([elem.get_text().strip() for elem in content_elems])
            
            # If no content found, try alternative selectors
            if not content.strip():
                content = self._extract_content_fallback(soup)
            
            return NewsArticle(
                source=self.config['name'],
                title=title,
                content=content,
                url=url,
                published_date=datetime.now(),
                category=self.config.get('category', 'general')
            )
            
        except Exception as e:
            print(f"Error parsing article page {url}: {str(e)}")
            return None
    
    def _extract_content_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback content extraction methods"""
        # Try common article content containers
        selectors = [
            'article .content',
            '.article-body',
            '.post-content',
            '.entry-content',
            'main article'
        ]
        
        for selector in selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                return content_elem.get_text().strip()
        
        return ""