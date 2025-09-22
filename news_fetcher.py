#!/usr/bin/env python3
"""
Main script to fetch news from multiple sources and save to JSON
"""

import time
from news_fetcher import get_fetcher, NEWS_SOURCES
from news_fetcher.utils import setup_logging, create_output_directory, save_to_json, generate_filename
from news_fetcher.config import OUTPUT_DIR, MAX_ARTICLES_PER_SOURCE

def fetch_single_source(source, max_articles):
    """Fetch news from a single source"""
    try:
        print(f"📍 Processing {source.name}...")
        fetcher = get_fetcher(source.name, source.base_url, source.rss_url)
        if fetcher:
            articles = fetcher.fetch_news(max_articles)
            result = {
                'source': source.name,
                'articles': articles,
                'count': len(articles)
            }
            
            if articles:
                print(f"✅ {source.name}: {len(articles)} articles")
            else:
                print(f"❌ {source.name}: Failed to fetch articles")
            
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
    
    print(f"\n📊 FETCHING SUMMARY")
    print(f"Total articles fetched: {total_articles}")
    
    for source_data in all_news:
        articles = source_data['articles']
        if not articles:
            continue
            
        print(f"\n{source_data['source']}:")
        print(f"  Articles: {source_data['count']}")
        
        # Count articles with authors
        has_authors = sum(1 for art in articles if art.get('authors'))
        print(f"  Articles with authors: {has_authors}/{source_data['count']}")

def main():
    """Main function"""
    print("🚀 Starting news fetcher...")
    print(f"📰 Sources: {[source.name for source in NEWS_SOURCES]}")
    print(f"📊 Target: {MAX_ARTICLES_PER_SOURCE} articles per source")
    print(f"💾 Output directory: {OUTPUT_DIR}")
    print("⏰ This may take a few minutes...")
    print("-" * 60)
    
    # Fetch all news
    all_news = fetch_all_news()
    
    if not all_news:
        print("❌ No news articles were fetched")
        return
    
    # Save data
    total_articles = save_news_data(all_news)
    
    print("\n" + "-" * 60)
    print(f"✅ COMPLETED! Fetched {total_articles} articles total")
    print(f"💾 Data saved to: {OUTPUT_DIR}/")
    
    # Print summary
    print("\n📊 SUMMARY:")
    for source_data in all_news:
        status = "✓" if source_data['count'] > 0 else "✗"
        print(f"   {status} {source_data['source']}: {source_data['count']} articles")
    
    # Additional analysis
    analyze_articles(all_news)
    
    print(f"\n🎯 Next step: Run 'python analysis.py' to analyze articles with AI")
    print("📋 Check 'news_fetcher.log' for detailed logs.")

if __name__ == "__main__":
    main()
