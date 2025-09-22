#!/usr/bin/env python3
"""
Test semantic understanding capabilities
"""

from vector_db import PurePythonVectorDB

def test_semantic_understanding():
    """Test if the system understands synonyms and related concepts"""
    vector_db = PurePythonVectorDB()
    
    # Load existing data
    if not vector_db.load_from_disk():
        print("❌ No data found. Run analysis.py first.")
        return
    
    test_cases = [
        {
            "query": "automobile industry",
            "expected_terms": ["car", "auto", "vehicle", "manufacturing"]
        },
        {
            "query": "climate change", 
            "expected_terms": ["global warming", "environment", "carbon", "emissions"]
        },
        {
            "query": "artificial intelligence",
            "expected_terms": ["AI", "machine learning", "neural networks", "technology"]
        },
        {
            "query": "economic news",
            "expected_terms": ["economy", "financial", "market", "business"]
        }
    ]
    
    print("🧠 Testing Semantic Understanding...")
    print("=" * 60)
    
    for test_case in test_cases:
        query = test_case["query"]
        expected_terms = test_case["expected_terms"]
        
        print(f"\n🔍 Query: '{query}'")
        print(f"   Expected to find: {expected_terms}")
        
        results = vector_db.semantic_search(query, k=5)
        
        if results:
            # Check if results contain expected terms
            found_terms = []
            for result in results:
                content = f"{result['title']} {result['snippet']}".lower()
                for term in expected_terms:
                    if term.lower() in content and term not in found_terms:
                        found_terms.append(term)
            
            print(f"   ✅ Found related terms: {found_terms}")
            print(f"   📊 Top result similarity: {results[0]['similarity']:.3f}")
            
        else:
            print("   ❌ No results found")

if __name__ == "__main__":
    test_semantic_understanding()
