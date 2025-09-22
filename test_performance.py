#!/usr/bin/env python3
"""
Performance testing for the search system
"""

import time
import os
from vector_db import PurePythonVectorDB
from analysis import load_news_articles

def test_performance():
    """Test search performance with proper error handling"""
    print("⏱️  Performance Testing")
    print("=" * 50)
    
    # Initialize vector DB
    vector_db = PurePythonVectorDB()
    
    # Try to load existing data
    if not vector_db.load_from_disk():
        print("❌ No vector database found. Please run analysis.py first.")
        print("💡 Run: python analysis.py")
        return
    
    # Check if we have data
    if not hasattr(vector_db, 'embeddings') or not vector_db.embeddings:
        print("❌ No embeddings found in database.")
        print("💡 Make sure analysis.py completed successfully.")
        return
    
    print(f"✅ Loaded database with {len(vector_db.embeddings)} articles")
    
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
                'similarity': results[0]['similarity'] if results else 0
            })
            
            print(f"🔍 '{query}'")
            print(f"   ⏰ Time: {response_time:.3f} seconds")
            print(f"   📊 Results: {len(results)}")
            if results:
                print(f"   🎯 Best similarity: {results[0]['similarity']:.3f}")
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
    
    vector_db = PurePythonVectorDB()
    
    # Check if data directory exists
    data_dir = "vector_db"
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
        if vector_db.load_from_disk():
            if hasattr(vector_db, 'embeddings') and vector_db.embeddings:
                print(f"✅ Database health: GOOD")
                print(f"📊 Articles loaded: {len(vector_db.embeddings)}")
                return True
            else:
                print("❌ Database loaded but no embeddings found")
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
    
    vector_db = PurePythonVectorDB()
    
    if not vector_db.load_from_disk():
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
                print(f"   {i+1}. {result['title'][:50]}... (sim: {result['similarity']:.3f})")
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
        print("1. python main.py          # Fetch news articles")
        print("2. python analysis.py      # Analyze articles with AI")
        print("3. python test_performance.py  # Run performance tests")
