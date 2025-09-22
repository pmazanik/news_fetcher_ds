# Test script to verify semantic search
def test_semantic_search():
    search_engine = PurePythonSearchEngine()
    
    test_queries = [
        "automobile industry",
        "climate change", 
        "artificial intelligence",
        "technology news",
        "iPhone release",
        "economic developments in Europe",
        "positive economic news", 
        "Middle East conflicts",
        "recent scientific discoveries",
        "renewable energy investments"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing: '{query}'")
        print("=" * 50)
        
        results = search_engine.vector_db.semantic_search(query, k=3)
        
        if results:
            for result in results:
                print(f"📰 {result['title']} (sim: {result['similarity']:.3f})")
                print(f"   Topics: {', '.join(result['topics'][:2])}")
        else:
            print("❌ No results found")
        
        print("-" * 50)
        input("Press Enter to continue...")

# Run the test
test_semantic_search()
