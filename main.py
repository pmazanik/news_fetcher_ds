#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from typing import List
from datetime import datetime
import signal

from strategies import StrategyFactory
from models.news_article import NewsArticle
from utils.helpers import load_config, save_articles_to_json, print_article_stats

class NewsFetcher:
    def __init__(self, config_path: str = "config/sources.json"):
        self.config_path = config_path
        try:
            self.sources_config = load_config(config_path)
        except FileNotFoundError:
            print(f"Configuration file not found: {config_path}")
            sys.exit(1)
    
    async def fetch_all_news(self) -> List[NewsArticle]:
        """Fetch news from all configured sources"""
        all_articles = []
        
        # Use task groups for better error handling (Python 3.11+)
        tasks = []
        
        for source_config in self.sources_config['sources']:
            try:
                strategy = StrategyFactory.create_strategy(
                    source_config['strategy'], 
                    source_config
                )
                task = asyncio.create_task(
                    self._fetch_source_articles(strategy, source_config)
                )
                tasks.append(task)
            except ValueError as e:
                print(f"Error creating strategy for {source_config.get('name', 'unknown')}: {e}")
        
        # Wait for all tasks to complete with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=300  # 5 minutes timeout
            )
            
            # Combine results
            for result in results:
                if isinstance(result, Exception):
                    print(f"Error in fetching task: {result}")
                elif isinstance(result, list):
                    all_articles.extend(result)
                    
        except asyncio.TimeoutError:
            print("Fetching timeout reached. Some articles may be incomplete.")
            # Cancel all pending tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
        
        return all_articles
    
    async def _fetch_source_articles(self, strategy, source_config: dict) -> List[NewsArticle]:
        """Fetch articles from a single source"""
        try:
            print(f"Fetching from {source_config['name']}...")
            articles = await strategy.fetch_articles(max_articles=20)
            
            # Clean up strategy resources
            await strategy.close_session()
            
            print(f"✓ Fetched {len(articles)} articles from {source_config['name']}")
            return articles
            
        except Exception as e:
            print(f"✗ Error fetching from {source_config['name']}: {str(e)}")
            await strategy.close_session()
            return []
    
    def analyze_articles(self, articles: List[NewsArticle]):
        """Basic analysis of articles"""
        if not articles:
            print("No articles to analyze.")
            return
            
        print("\n=== BASIC CONTENT ANALYSIS ===")
        
        # Word frequency analysis
        from collections import Counter
        import string
        
        all_text = ' '.join(article.content.lower() for article in articles)
        
        # Remove punctuation and filter words
        translator = str.maketrans('', '', string.punctuation)
        clean_text = all_text.translate(translator)
        
        words = [word for word in clean_text.split() if len(word) > 3 and word.isalpha()]
        common_words = Counter(words).most_common(15)
        
        print("Most common words (excluding short words and numbers):")
        for i, (word, count) in enumerate(common_words, 1):
            print(f"  {i:2d}. {word:12} : {count:3d}")
        
        # Content length distribution
        lengths = [len(article.content.split()) for article in articles]
        if lengths:
            print(f"\nContent length distribution:")
            print(f"  Shortest: {min(lengths):,} words")
            print(f"  Longest: {max(lengths):,} words")
            print(f"  Average: {sum(lengths)/len(lengths):,.0f} words")
            
            # Quality assessment
            short_articles = len([l for l in lengths if l < 100])
            long_articles = len([l for l in lengths if l > 500])
            print(f"  Short articles (<100 words): {short_articles}")
            print(f"  Long articles (>500 words): {long_articles}")
        
        # Sources analysis
        source_stats = {}
        for article in articles:
            if article.source not in source_stats:
                source_stats[article.source] = []
            source_stats[article.source].append(len(article.content.split()))
        
        print(f"\nAverage words by source:")
        for source, word_counts in source_stats.items():
            avg_words = sum(word_counts) / len(word_counts)
            print(f"  {source}: {avg_words:,.0f} words")

async def main():
    """Main function with proper error handling"""
    print("🚀 Starting News Fetcher (Python 3.11 Compatible)...")
    
    # Setup signal handling for graceful shutdown
    def signal_handler():
        print("\nShutting down gracefully...")
        # Additional cleanup can be added here
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Initialize fetcher
        fetcher = NewsFetcher()
        
        # Fetch articles
        articles = await fetcher.fetch_all_news()
        
        if not articles:
            print("No articles were fetched. Check your configuration and internet connection.")
            return
        
        # Print statistics
        print_article_stats(articles)
        
        # Perform basic analysis
        fetcher.analyze_articles(articles)
        
        # Save to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"news_articles_{timestamp}.json"
        save_articles_to_json(articles, output_file)
        
        print(f"\n✅ Articles saved to: {output_file}")
        print(f"📊 Total articles processed: {len(articles)}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("config", exist_ok=True)
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("utils", exist_ok=True)
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        sys.exit(1)
    
    # Run the main function
    asyncio.run(main())