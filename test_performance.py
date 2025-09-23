#!/usr/bin/env python3
"""
Performance testing for the search system
"""

import time
import os
from vector_db import LangChainVectorDB
from analysis import load_news_articles
from news_fetcher.config import OUTPUT_DIR, ANALYSIS_DIR, VECTOR_DB_DIR

def test_performance():
    """Test search performance with proper error handling"""
    print("⏱️  Performance Testing")
    print("=" * 50)
    print(f"📁 Using vector database from: {VECTOR_DB_DIR}")
    
    # Initialize vector DB
    vector_db = LangChainVectorDB()
    
    # Try to load existing data
    if not vector_db.load_articles():
        print(f"❌ No vector database found in {VECTOR_DB_DIR}. Please run analysis.py first.")
        print("💡 Run: python analysis.py")
        return
    
    # Check if we have data
    stats = vector_db.get_database_stats()
    if stats['status'] != 'loaded':
        print("❌ Database not loaded properly.")
        return
    
    print(f"✅ Loaded database with {stats.get('document_count', 0)} articles")
    print(f"🤖 Using model: {stats.get('embedding_model', 'Unknown')}")
    
    test_queries = [
        "technology",
        "politics", 
        "sports",
        "health",
        "business",
        "climate change",
        "artificial intelligence",
        "economic news"
    ]
    
    print(f"🧪 Testing {len(test_queries)} queries...")
    print()
    
    performance_results = []
    
    for query in test_queries:
        start_time = time.time()
        
        try:
            # Test search speed
            results = vector_db.semantic_search(query, k=3)
            end_time = time.time()
            response_time = end_time - start_time
            
            performance_results.append({
                'query': query,
                'time': response_time,
                'results': len(results),
                'similarity': results[0]['similarity_score'] if results else 0
            })
            
            print(f"🔍 '{query}'")
            print(f"   ⏰ Time: {response_time:.3f} seconds")
            print(f"   📊 Results: {len(results)}")
            if results:
                print(f"   🎯 Best similarity: {results[0]['similarity_score']:.3f}")
            print()
            
        except Exception as e:
            print(f"❌ Error testing query '{query}': {e}")
            continue
    
    # Summary statistics
    if performance_results:
        print("📈 Performance Summary")
        print("=" * 30)
        
        avg_time = sum(r['time'] for r in performance_results) / len(performance_results)
        avg_results = sum(r['results'] for r in performance_results) / len(performance_results)
        avg_similarity = sum(r['similarity'] for r in performance_results) / len(performance_results)
        
        print(f"📊 Average search time: {avg_time:.3f} seconds")
        print(f"📊 Average results per query: {avg_results:.1f}")
        print(f"📊 Average similarity score: {avg_similarity:.3f}")
        print(f"📊 Total queries tested: {len(performance_results)}")
        
        # Show fastest and slowest queries
        fastest = min(performance_results, key=lambda x: x['time'])
        slowest = max(performance_results, key=lambda x: x['time'])
        
        print(f"⚡ Fastest query: '{fastest['query']}' ({fastest['time']:.3f}s)")
        print(f"🐌 Slowest query: '{slowest['query']}' ({slowest['time']:.3f}s)")
    
    else:
        print("❌ No performance data collected.")

def test_database_health():
    """Check if the database is properly set up"""
    print("🏥 Database Health Check")
    print("=" * 30)
    print(f"📁 Checking directories:")
    print(f"   News data: {OUTPUT_DIR}")
    print(f"   Analysis: {ANALYSIS_DIR}")
    print(f"   Vector DB: {VECTOR_DB_DIR}")
    
    vector_db = LangChainVectorDB()
    
    # Check if data directory exists
    data_dir = VECTOR_DB_DIR
    if not os.path.exists(data_dir):
        print("❌ Vector database directory not found")
        return False
    
    # Check if data file exists
    data_file = os.path.join(data_dir, "data.json")
    if not os.path.exists(data_file):
        print("❌ Vector database file not found")
        return False
    
    # Try to load data
    try:
        if vector_db.load_articles():
            stats = vector_db.get_database_stats()
            if stats['status'] == 'loaded':
                print(f"✅ Database health: GOOD")
                print(f"📊 Articles loaded: {stats.get('document_count', 'Unknown')}")
                print(f"🔧 Embedding model: {stats.get('embedding_model', 'Unknown')}")
                return True
            else:
                print("❌ Database loaded but status not 'loaded'")
                return False
        else:
            print("❌ Failed to load database")
            return False
    except Exception as e:
        print(f"❌ Error loading database: {e}")
        return False

def test_simple_search():
    """Simple test to verify search works"""
    print("🔍 Simple Search Test")
    print("=" * 30)
    
    vector_db = LangChainVectorDB()
    
    if not vector_db.load_articles():
        print("❌ Cannot load database")
        return
    
    # Test a simple query
    test_query = "technology"
    print(f"Testing query: '{test_query}'")
    
    try:
        results = vector_db.semantic_search(test_query, k=2)
        
        if results:
            print(f"✅ Search working! Found {len(results)} results")
            for i, result in enumerate(results):
                print(f"   {i+1}. {result['title'][:50]}... (sim: {result['similarity_score']:.3f})")
        else:
            print("❌ No results found")
            
    except Exception as e:
        print(f"❌ Search error: {e}")

if __name__ == "__main__":
    print("🎯 News Fetcher Performance Tests")
    print("=" * 50)
    
    # First, check database health
    if test_database_health():
        print("\n" + "="*50)
        
        # Run simple search test
        test_simple_search()
        
        print("\n" + "="*50)
        
        # Run full performance test
        test_performance()
    else:
        print("\n💡 Solution: Run these commands first:")
        print("1. python news_fetcher.py    # Fetch news articles")
        print("2. python analysis.py        # Analyze articles with AI")
        print("3. python test_performance.py  # Run performance tests")
