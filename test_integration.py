#!/usr/bin/env python3
"""
Full integration test
"""

from analysis import load_news_articles, SimpleNewsAnalyzer
from vector_db import PurePythonVectorDB

def integration_test():
    """Full integration test from articles to search"""
    print("🔗 Integration Test")
    print("=" * 50)
    
    # Step 1: Load articles
    articles = load_news_articles()
    print(f"1. Loaded {len(articles)} articles")
    
    # Step 2: Analyze sample
    analyzer = SimpleNewsAnalyzer()
    sample_articles = articles[:10]  # Use 10 for testing
    analysis_results = analyzer.analyze_articles_batch(sample_articles)
    print(f"2. Analyzed {len(analysis_results)} articles")
    
    # Step 3: Store in vector DB
    vector_db = PurePythonVectorDB()
    success = vector_db.store_articles(analysis_results)
    print(f"3. Stored in vector DB: {success}")
    
    # Step 4: Test searches
    test_searches = [
        ("technology", "Should find tech-related articles"),
        ("climate", "Should find environment-related articles"),
        ("economy", "Should find business/finance articles")
    ]
    
    for query, description in test_searches:
        print(f"\n4. Testing: {description}")
        results = vector_db.semantic_search(query, k=3)
        print(f"   Query: '{query}' → Found: {len(results)} results")
        if results:
            print(f"   Best match: {results[0]['title'][:50]}...")
    
    print("\n✅ Integration test completed!")

if __name__ == "__main__":
    integration_test()
