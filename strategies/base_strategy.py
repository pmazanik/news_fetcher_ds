from abc import ABC, abstractmethod
from typing import List, Optional
from models.news_article import NewsArticle
import aiohttp
import asyncio

class BaseNewsStrategy(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.session = None
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def create_session(self):
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                connector=connector
            )
    
    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    @abstractmethod
    async def fetch_articles(self, max_articles: int = 20) -> List[NewsArticle]:
        pass
    
    async def fetch_url(self, url: str, headers: Optional[dict] = None) -> Optional[str]:
        """Common method to fetch URL content with proper headers"""
        try:
            await self.create_session()
            
            default_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            if headers:
                default_headers.update(headers)
                
            async with self.session.get(url, headers=default_headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Failed to fetch {url}: Status {response.status}")
                    return None
        except asyncio.TimeoutError:
            print(f"Timeout fetching {url}")
            return None
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None