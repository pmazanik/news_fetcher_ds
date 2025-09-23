import json
import asyncio
from typing import List, Dict, Any
from models.news_article import NewsArticle
from datetime import datetime

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_articles_to_json(articles: List[NewsArticle], filename: str):
    """Save articles to JSON file"""
    data = {
        'fetch_date': datetime.now().isoformat(),
        'total_articles': len(articles),
        'articles': [article.to_dict() for article in articles]
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def print_article_stats(articles: List[NewsArticle]):
    """Print statistics about fetched articles"""
    if not articles:
        print("No articles fetched.")
        return
    
    print(f"\n=== FETCHING STATISTICS ===")
    print(f"Total articles: {len(articles)}")
    
    # Group by source
    sources = {}
    for article in articles:
        sources[article.source] = sources.get(article.source, 0) + 1
    
    print("\nArticles by source:")
    for source, count in sources.items():
        print(f"  {source}: {count} articles")
    
    # Content statistics
    total_words = sum(len(article.content.split()) for article in articles)
    avg_words = total_words / len(articles)
    
    print(f"\nContent statistics:")
    print(f"  Total words: {total_words:,}")
    print(f"  Average words per article: {avg_words:,.0f}")
    
    # Longest articles
    longest_articles = sorted(articles, key=lambda x: len(x.content.split()), reverse=True)[:3]
    print(f"\nLongest articles:")
    for i, article in enumerate(longest_articles, 1):
        words = len(article.content.split())
        print(f"  {i}. {article.source}: {words:,} words - {article.title[:60]}...")