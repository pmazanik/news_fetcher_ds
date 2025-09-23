from typing import List
from strategies.base_strategy import BaseNewsStrategy
from models.news_article import NewsArticle
from bs4 import BeautifulSoup
import aiohttp
from datetime import datetime
from urllib.parse import urljoin
import asyncio
import io
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    try:
        import pypdf
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False

class PDFStrategy(BaseNewsStrategy):
    async def fetch_articles(self, max_articles: int = 20) -> List[NewsArticle]:
        if not PDF_SUPPORT:
            print("PDF support not available. Install PyPDF2 or pypdf.")
            return []
            
        articles = []
        
        try:
            # Fetch the papers listing page
            html = await self.fetch_url(self.config['url'])
            if not html:
                return articles
            
            soup = BeautifulSoup(html, 'html.parser')
            pdf_config = self.config.get('pdf_config', {})
            base_url = pdf_config.get('base_url', self.config['url'])
            
            # Find PDF links
            pdf_links = soup.select(pdf_config.get('paper_selector', 'a[href*=".pdf"]'))
            
            processed_articles = 0
            for link in pdf_links[:max_articles]:
                try:
                    pdf_url = link.get('href')
                    if not pdf_url:
                        continue
                    
                    # Make absolute URL
                    if not pdf_url.startswith('http'):
                        pdf_url = urljoin(base_url, pdf_url)
                    
                    # Extract title
                    title = self._extract_title(soup, link, pdf_config)
                    
                    # Fetch and parse PDF
                    content = await self._extract_pdf_content(pdf_url)
                    
                    if content:
                        article = NewsArticle(
                            source=self.config['name'],
                            title=title,
                            content=content,
                            url=pdf_url,
                            published_date=datetime.now(),
                            category=self.config.get('category', 'research'),
                            metadata={'document_type': 'PDF'}
                        )
                        articles.append(article)
                        processed_articles += 1
                        
                except Exception as e:
                    print(f"Error processing PDF: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error in PDF strategy: {str(e)}")
        
        return articles
    
    def _extract_title(self, soup: BeautifulSoup, link, pdf_config: dict) -> str:
        """Extract paper title"""
        title_selector = pdf_config.get('title_selector', '')
        if title_selector:
            title_elem = soup.select_one(title_selector)
            if title_elem:
                return title_elem.get_text().strip()
        
        # Fallback: use link text or parent text
        return link.get_text().strip() or "Research Paper"
    
    async def _extract_pdf_content(self, pdf_url: str) -> str:
        """Extract text content from PDF"""
        if not PDF_SUPPORT:
            return ""
            
        try:
            await self.create_session()
            async with self.session.get(pdf_url) as response:
                if response.status == 200:
                    pdf_data = await response.read()
                    
                    # Use thread pool for PDF parsing (CPU-bound)
                    loop = asyncio.get_event_loop()
                    text = await loop.run_in_executor(None, self._parse_pdf, pdf_data)
                    return text
                else:
                    print(f"Failed to download PDF: {response.status}")
                    return ""
        except Exception as e:
            print(f"Error extracting PDF content: {str(e)}")
            return ""
    
    def _parse_pdf(self, pdf_data: bytes) -> str:
        """Parse PDF content synchronously"""
        try:
            pdf_file = io.BytesIO(pdf_data)
            
            # Try different PDF libraries for compatibility
            try:
                # Try PyPDF2 first
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except Exception:
                # Fallback to pypdf if available
                try:
                    import pypdf
                    pdf_reader = pypdf.PdfReader(pdf_file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                except ImportError:
                    return "PDF parsing not available"
                    
        except Exception as e:
            print(f"Error parsing PDF: {str(e)}")
            return ""