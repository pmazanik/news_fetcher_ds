#!/usr/bin/env python3
"""
Test script for the semantic search solution
"""

from vector_db import PurePythonVectorDB
from analysis import load_news_articles, SimpleNewsAnalyzer

def test_basic_functionality():
    """Test if the basic components work"""
    print("🧪 Testing Basic Functionality...")
    print("=" * 50)
    
    # Test 1: Load articles
    articles = load_news_articles()
    print(f"✅ Loaded {len(articles)} articles")
    
    # Test 2: Initialize analyzer
    analyzer = SimpleNewsAnalyzer()
    print("✅ Analyzer initialized")
    
    # Test 3: Initialize vector DB
    vector_db = PurePythonVectorDB()
    print("✅ Vector DB initialized")
    
    # Test 4: Analyze a few articles
    sample_articles = articles[:3]  # Just 3 for testing
    analysis_results = analyzer.analyze_articles_batch(sample_articles)
    print(f"✅ Analyzed {len(analysis_results)} articles")
    
    # Test 5: Store in vector DB
    success = vector_db.store_articles(analysis_results)
    print(f"✅ Articles stored in vector DB: {success}")
    
    return vector_db

def run_tests():
    """Run all tests"""
    vector_db = test_basic_functionality()
    
    # Test semantic search with various queries
    test_queries = [
        "technology news",
        "climate change",
        "economic developments",
        "healthcare updates",
        "sports news"
    ]
    
    print("\n🔍 Testing Semantic Search...")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        results = vector_db.semantic_search(query, k=3)
        
        if results:
            print(f"✅ Found {len(results)} results")
            for result in results[:2]:  # Show top 2 results
                print(f"   - {result['title']} (similarity: {result['similarity']:.3f})")
        else:
            print("❌ No results found")
    
    # Test question answering
    print("\n❓ Testing Question Answering...")
    print("=" * 50)
    
    test_questions = [
        "What are the main technology trends?",
        "Tell me about recent climate developments",
        "What's happening in the economy?"
    ]
    
    for question in test_questions:
        print(f"\nQ: {question}")
        answer = vector_db.ask_question(question)
        
        if 'error' in answer:
            print(f"❌ Error: {answer['error']}")
        else:
            print(f"✅ Answer: {answer['answer'][:100]}...")
            if answer.get('sources'):
                print(f"   Sources: {len(answer['sources'])} articles referenced")

if __name__ == "__main__":
    run_tests()
