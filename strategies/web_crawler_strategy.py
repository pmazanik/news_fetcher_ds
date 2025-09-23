from typing import List
from strategies.base_strategy import BaseNewsStrategy
from models.news_article import NewsArticle
from bs4 import BeautifulSoup
import aiohttp
from datetime import datetime
import asyncio
from urllib.parse import urljoin
import re

class WebCrawlerStrategy(BaseNewsStrategy):
    async def fetch_articles(self, max_articles: int = 20) -> List[NewsArticle]:
        articles = []
        
        try:
            print(f"🌐 Crawling {self.config['name']}...")
            
            # Fetch the main page
            html = await self.fetch_url(self.config['url'])
            if not html:
                print(f"❌ Failed to fetch main page: {self.config['url']}")
                return articles
            
            soup = BeautifulSoup(html, 'html.parser')
            crawler_config = self.config.get('crawler_config', {})
            
            # Find article links
            article_selector = crawler_config.get('article_selector', 'a')
            article_links = soup.select(article_selector)
            base_url = crawler_config.get('base_url', self.config['url'])
            
            print(f"🔗 Found {len(article_links)} potential articles on {self.config['name']}")
            
            processed_articles = 0
            for i, link in enumerate(article_links):
                if processed_articles >= max_articles:
                    break
                
                try:
                    article_url = link.get('href')
                    if not article_url:
                        continue
                    
                    # Make absolute URL
                    if not article_url.startswith('http'):
                        article_url = urljoin(base_url, article_url)
                    
                    # Skip non-article URLs
                    if not self._is_article_url(article_url):
                        continue
                    
                    print(f"📖 Processing article {processed_articles + 1}/{max_articles}: {article_url}")
                    
                    # Fetch and parse individual article
                    article = await self._parse_article_page(article_url)
                    if article and article.content.strip() and len(article.content) > 100:
                        articles.append(article)
                        processed_articles += 1
                        print(f"✅ Added article from {self.config['name']}: {article.title[:60]}...")
                    else:
                        print(f"⏩ Skipped article (insufficient content)")
                        
                except Exception as e:
                    print(f"❌ Error processing article link: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"💥 Error in web crawler for {self.config['name']}: {str(e)}")
        
        print(f"🎯 Successfully crawled {len(articles)} articles from {self.config['name']}")
        return articles
    
    def _is_article_url(self, url: str) -> bool:
        """Check if URL looks like an article"""
        article_indicators = [
            '/article/', '/news/', '/story/', '/blog/',
            '/202', '/2023/', '/2024/', '/research/', '/paper/'
        ]
        
        non_article_indicators = [
            '/category/', '/tag/', '/author/', '/page/',
            '/login', '/signup', '/subscribe', '/contact'
        ]
        
        url_lower = url.lower()
        
        # Check for article indicators
        has_article_indicator = any(indicator in url_lower for indicator in article_indicators)
        
        # Check for non-article indicators
        has_non_article_indicator = any(indicator in url_lower for indicator in non_article_indicators)
        
        return has_article_indicator and not has_non_article_indicator
    
    async def _parse_article_page(self, url: str) -> NewsArticle:
        """Parse individual article page with better content extraction"""
        try:
            html = await self.fetch_url(url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            crawler_config = self.config.get('crawler_config', {})
            
            # Extract title with multiple fallbacks
            title = self._extract_title(soup, crawler_config)
            
            # Extract content with multiple strategies
            content = self._extract_content(soup, crawler_config)
            
            # If content is too short, try alternative extraction methods
            if len(content.strip()) < 200:
                content = self._extract_content_fallback(soup)
            
            # If still no content, skip this article
            if len(content.strip()) < 100:
                return None
            
            return NewsArticle(
                source=self.config['name'],
                title=title,
                content=content,
                url=url,
                published_date=datetime.now(),
                category=self.config.get('category', 'general'),
                metadata={'crawled_url': url}
            )
            
        except Exception as e:
            print(f"❌ Error parsing article page {url}: {str(e)}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup, crawler_config: dict) -> str:
        """Extract title with multiple fallbacks"""
        title_selector = crawler_config.get('title_selector', 'h1')
        title_elem = soup.select_one(title_selector)
        
        if title_elem:
            title = title_elem.get_text().strip()
            if title:
                return title
        
        # Fallback title selectors
        fallback_selectors = [
            'h1.article-title', 'h1.title', 'h1.headline',
            'title', 'meta[property="og:title"]'
        ]
        
        for selector in fallback_selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get('content') if selector.startswith('meta') else elem.get_text()
                if title and title.strip():
                    return title.strip()
        
        return "No Title Found"
    
    def _extract_content(self, soup: BeautifulSoup, crawler_config: dict) -> str:
        """Extract content with the configured selector"""
        content_selector = crawler_config.get('content_selector', 'p')
        content_elems = soup.select(content_selector)
        
        if content_elems:
            content = ' '.join([elem.get_text().strip() for elem in content_elems])
            # Clean up extra whitespace
            content = re.sub(r'\s+', ' ', content)
            return content.strip()
        
        return ""
    
    def _extract_content_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback content extraction methods"""
        # Try common article content containers
        content_selectors = [
            'article .content',
            '.article-body',
            '.post-content',
            '.entry-content',
            'main article',
            '.story-content',
            '.article-text',
            '#article-content'
        ]
        
        for selector in content_selectors:
            content_elems = soup.select(selector)
            if content_elems:
                content = ' '.join([elem.get_text().strip() for elem in content_elems])
                content = re.sub(r'\s+', ' ', content)
                if len(content) > 100:
                    return content.strip()
        
        # Try to extract all paragraphs within article tags
        article_elem = soup.find('article')
        if article_elem:
            paragraphs = article_elem.find_all('p')
            if paragraphs:
                content = ' '.join([p.get_text().strip() for p in paragraphs])
                content = re.sub(r'\s+', ' ', content)
                return content.strip()
        
        return ""