#!/usr/bin/env python3
"""
Main script with enhanced date checking for recent news
"""

import time
from datetime import datetime, timedelta
from news_fetcher import get_fetcher, NEWS_SOURCES
from news_fetcher.utils import setup_logging, create_output_directory, save_to_json, generate_filename
from news_fetcher.config import OUTPUT_DIR, MAX_ARTICLES_PER_SOURCE

def is_recent_article(article_data: dict, max_days_old: int = 2) -> bool:
    """Check if article is recent"""
    publish_date = article_data.get('publish_date')
    if not publish_date:
        return False

    try:
        if isinstance(publish_date, str):
            # Try to parse various date formats
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d %b %Y', '%b %d, %Y'):
                try:
                    publish_date = datetime.strptime(publish_date, fmt)
                    break
                except:
                    continue

        if isinstance(publish_date, datetime):
            return (datetime.now() - publish_date).days <= max_days_old

    except Exception as e:
        print(f"Date parsing error: {e}")

    return False

def fetch_single_source(source, max_articles):
    """Fetch news from a single source with recency check"""
    try:
        print(f"📍 Processing {source.name}...")
        fetcher = get_fetcher(source.name, source.base_url, source.rss_url)
        if fetcher:
            articles = fetcher.fetch_news(max_articles)

            # Filter for recent articles only
            recent_articles = []
            for article in articles:
                if is_recent_article(article) or not article.get('publish_date'):
                    recent_articles.append(article)

            result = {
                'source': source.name,
                'articles': recent_articles,
                'count': len(recent_articles),
                'total_fetched': len(articles)
            }

            if recent_articles:
                print(f"✅ {source.name}: {len(recent_articles)} recent articles (out of {len(articles)} total)")
            else:
                print(f"⚠️  {source.name}: No recent articles found ({len(articles)} total)")

            return result
    except Exception as e:
        print(f"❌ {source.name}: Error - {e}")
    return None

def fetch_all_news():
    """Fetch news from all sources sequentially"""
    setup_logging()
    create_output_directory(OUTPUT_DIR)
    
    all_news = []
    
    # Process sources sequentially to avoid overwhelming servers
    for source in NEWS_SOURCES:
        result = fetch_single_source(source, MAX_ARTICLES_PER_SOURCE)
        if result:
            all_news.append(result)
        time.sleep(2)  # Brief pause between sources
    
    return all_news

def save_news_data(all_news):
    """Save news data to JSON files"""
    # Save combined data
    combined_data = []
    for source_data in all_news:
        combined_data.extend(source_data['articles'])
    
    combined_filename = f"{OUTPUT_DIR}/all_news_combined.json"
    save_to_json(combined_data, combined_filename)
    
    # Save individual source data
    for source_data in all_news:
        if source_data['articles']:
            source_name = source_data['source']
            filename = f"{OUTPUT_DIR}/{generate_filename(source_name)}"
            save_to_json(source_data['articles'], filename)
    
    return len(combined_data)

def analyze_articles(all_news):
    """Analyze and display statistics about fetched articles"""
    total_articles = sum(source['count'] for source in all_news)
    
    print(f"\nArticle Analysis:")
    print(f"Total articles: {total_articles}")
    
    for source_data in all_news:
        articles = source_data['articles']
        if not articles:
            continue
            
        avg_title_len = sum(len(art['title']) for art in articles) / len(articles)
        avg_text_len = sum(len(art['text']) for art in articles) / len(articles)
        
        print(f"\n{source_data['source']}:")
        print(f"  Articles: {source_data['count']}")
        print(f"  Avg title length: {avg_title_len:.1f} chars")
        print(f"  Avg text length: {avg_text_len:.1f} chars")
        
        # Count articles with authors
        has_authors = sum(1 for art in articles if art.get('authors'))
        print(f"  Articles with authors: {has_authors}/{source_data['count']}")

def main():
    """Main function"""
    print("Starting news fetcher...")
    print("Sources: BBC, CNN, The Guardian, AP News")
    print("Target: 20 articles per source")
    print("This may take a few minutes...")
    print("-" * 50)
    
    # Fetch all news
    all_news = fetch_all_news()
    
    if not all_news:
        print("No news articles were fetched")
        return
    
    # Save data
    total_articles = save_news_data(all_news)
    
    print("\n" + "-" * 50)
    print(f"COMPLETED! Fetched {total_articles} articles total")
    print(f"Data saved to: {OUTPUT_DIR}/")
    
    # Print summary
    print("\nSUMMARY:")
    for source_data in all_news:
        status = "✓" if source_data['count'] > 0 else "✗"
        print(f"   {status} {source_data['source']}: {source_data['count']} articles")
    
    # Additional analysis
    analyze_articles(all_news)
    
    print("\nCheck 'news_fetcher.log' for detailed logs.")

if __name__ == "__main__":
    main()
