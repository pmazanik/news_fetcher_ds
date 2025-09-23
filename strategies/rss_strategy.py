import feedparser
from typing import List
from datetime import datetime
from strategies.base_strategy import BaseNewsStrategy
from models.news_article import NewsArticle
import asyncio
from newspaper import Article, ArticleException
import aiohttp
import ssl

class RSSStrategy(BaseNewsStrategy):
    async def fetch_articles(self, max_articles: int = 20) -> List[NewsArticle]:
        articles = []
        
        try:
            # Create custom SSL context to handle certificate issues
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Parse RSS feed with timeout
            feed = feedparser.parse(self.config['url'])
            
            if not feed.entries:
                print(f"⚠️ No entries found in RSS feed: {self.config['url']}")
                print(f"Feed status: {feed.get('status', 'Unknown')}")
                return articles
            
            print(f"📋 Found {len(feed.entries)} entries in {self.config['name']}")
            
            for i, entry in enumerate(feed.entries[:max_articles]):
                try:
                    title = entry.get('title', 'No Title').strip()
                    url = entry.get('link', '')
                    
                    if not url:
                        print(f"⏩ Skipping entry with no URL: {title[:50]}...")
                        continue
                    
                    # Clean URL (remove tracking parameters, etc.)
                    url = self._clean_url(url)
                    
                    published_date = self._parse_date(entry)
                    
                    print(f"📰 Processing {i+1}/{min(len(feed.entries), max_articles)}: {title[:60]}...")
                    
                    # Fetch full content using newspaper3k with timeout
                    content = await self._fetch_full_content(url)
                    
                    if not content or len(content.strip()) < 100:
                        # Fallback to RSS content
                        content = entry.get('summary', entry.get('description', ''))
                        if not content:
                            content = entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
                    
                    # Ensure we have some content
                    if not content.strip():
                        content = f"Title: {title}. Source: {self.config['name']}. Full article available at: {url}"
                    
                    # Create summary
                    summary = self._create_summary(content, entry.get('summary'))
                    
                    article = NewsArticle(
                        source=self.config['name'],
                        title=title,
                        content=content,
                        url=url,
                        published_date=published_date,
                        category=self.config.get('category', 'general'),
                        summary=summary,
                        metadata={
                            'rss_feed': self.config['url'],
                            'content_source': 'newspaper3k' if len(content) > len(summary or '') else 'rss'
                        }
                    )
                    
                    articles.append(article)
                    print(f"✅ Added article: {title[:50]}... ({len(content)} chars)")
                    
                except Exception as e:
                    print(f"❌ Error processing RSS entry: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"💥 Error fetching RSS feed {self.config['name']} ({self.config['url']}): {str(e)}")
        
        print(f"🎯 Successfully fetched {len(articles)} articles from {self.config['name']}")
        return articles
    
    def _clean_url(self, url: str) -> str:
        """Clean URL by removing common tracking parameters"""
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(url)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # Remove tracking parameters
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'gclid']
            for param in tracking_params:
                query_params.pop(param, None)
            
            # Rebuild URL
            new_query = urllib.parse.urlencode(query_params, doseq=True)
            cleaned_url = urllib.parse.urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))
            return cleaned_url
        except:
            return url
    
    def _parse_date(self, entry) -> datetime:
        """Parse various date formats from RSS feeds with better error handling"""
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
        
        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    return datetime(*getattr(entry, field)[:6])
                except (TypeError, ValueError) as e:
                    print(f"⚠️ Date parsing error for {field}: {e}")
                    continue
        
        # Fallback to current date
        return datetime.now()
    
    def _create_summary(self, content: str, rss_summary: str = None) -> str:
        """Create a summary from content"""
        if rss_summary and len(rss_summary) > 50:
            return rss_summary[:300] + '...' if len(rss_summary) > 300 else rss_summary
        
        if content:
            # Take first 300 characters as summary
            summary = content[:300].strip()
            if len(content) > 300:
                summary += '...'
            return summary
        
        return None
    
    async def _fetch_full_content(self, url: str) -> str:
        """Fetch full article content using newspaper3k with better error handling"""
        try:
            # Set timeout for content fetching
            loop = asyncio.get_event_loop()
            content = await asyncio.wait_for(
                loop.run_in_executor(None, self._extract_with_newspaper, url),
                timeout=30.0
            )
            return content
        except asyncio.TimeoutError:
            print(f"⏰ Timeout fetching content from {url}")
            return ""
        except Exception as e:
            print(f"⚠️ Error extracting content from {url}: {str(e)}")
            return ""
    
    def _extract_with_newspaper(self, url: str) -> str:
        """Extract article content using newspaper3k (sync)"""
        try:
            # Configure newspaper
            article = Article(url)
            article.download()
            article.parse()
            
            # Get text and clean it
            text = article.text.strip()
            
            # If text is too short, try alternative extraction
            if len(text) < 100:
                # Try to get meta description or first few paragraphs
                if article.meta_description:
                    text = article.meta_description
                elif article.title:
                    text = f"{article.title}. {article.meta_description or 'Full article available at the source.'}"
            
            return text
            
        except ArticleException as e:
            print(f"📰 Newspaper3k error for {url}: {str(e)}")
            return ""
        except Exception as e:
            print(f"💥 Unexpected error in newspaper3k for {url}: {str(e)}")
            return ""