import json
import os
from datetime import datetime
import logging
import requests
from newspaper import Article
import random
import time
import re
from bs4 import BeautifulSoup
from .config import USER_AGENTS, TIMEOUT, REQUEST_DELAY

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('news_fetcher.log'),
            logging.StreamHandler()
        ]
    )

def create_output_directory(directory: str):
    """Create output directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")

#def save_to_json(data: list, filename: str):
#    """Save data to JSON file"""
#    try:
#       with open(filename, 'w', encoding='utf-8') as f:
#            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
#        logging.info(f"Saved {len(data)} articles to {filename}")
#    except Exception as e:
#        logging.error(f"Error saving to JSON: {e}")

def save_to_json(data: list, filename: str):
    """Save data to JSON file with metadata"""
    try:
        # Check if data is already in the new format with metadata
        if isinstance(data, dict) and 'articles' in data:
            # Data is already in the correct format
            json_data = data
        else:
            # Create new format with metadata
            source = data[0]['source'] if data and isinstance(data, list) and len(data) > 0 else "unknown"
            json_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_articles": len(data),
                    "source": source,
                    "version": "1.0"
                },
                "articles": data
            }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
        logging.info(f"Saved {len(data)} articles to {filename}")
    except Exception as e:
        logging.error(f"Error saving to JSON: {e}")

def generate_filename(source_name: str) -> str:
    """Generate filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{source_name.lower()}_news_{timestamp}.json"

def get_random_user_agent():
    """Get random user agent from list"""
    return random.choice(USER_AGENTS)

def create_session():
    """Create requests session with proper headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session

def fetch_article_content(url: str, source_name: str) -> dict:
    """Fetch full article content using newspaper3k"""
    try:
        article = Article(url)
        article.download()
        article.parse()

        article_data = {
            'title': article.title,
            'text': article.text,
            'publish_date': article.publish_date,
            'authors': article.authors,
            'url': url,
            'source': source_name,
            'summary': article.summary if hasattr(article, 'summary') else '',
        }

        # Validate article quality
        if validate_article(article_data):
            return article_data
        return None

    except Exception as e:
        logging.warning(f"Error fetching article {url}: {e}")
        return None

def respectful_delay():
    """Add random delay between requests using configured delay"""
    delay = random.uniform(REQUEST_DELAY * 0.5, REQUEST_DELAY * 1.5)
    time.sleep(delay)

def validate_article(article_data: dict) -> bool:
    """Validate that article has meaningful content"""
    if not article_data:
        return False
    
    # Check for essential fields
    required_fields = ['title', 'text', 'url']
    for field in required_fields:
        if not article_data.get(field):
            return False
    
    # Check minimum content length
    if len(article_data.get('text', '').strip()) < 200:
        return False
    
    # Check title length
    if len(article_data.get('title', '').strip()) < 10:
        return False
    
    return True
