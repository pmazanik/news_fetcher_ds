#!/usr/bin/env python3
"""
Diagnostic script to check data at each stage
"""

import json
import os
from analysis import load_news_articles
from news_fetcher.config import OUTPUT_DIR, ANALYSIS_DIR, VECTOR_DB_DIR, MAX_ARTICLES_PER_SOURCE, MODEL, EMBEDDING_MODEL

def check_data_pipeline():
    """Check data at each stage of the pipeline"""
    print("🔍 Data Pipeline Diagnostic")
    print("=" * 50)
    print(f"⚙️  Configuration:")
    print(f"   MAX_ARTICLES_PER_SOURCE: {MAX_ARTICLES_PER_SOURCE}")
    print(f"   MODEL: {MODEL}")
    print(f"   EMBEDDING_MODEL: {EMBEDDING_MODEL}")
    print(f"   OUTPUT_DIR: {OUTPUT_DIR}")
    print(f"   ANALYSIS_DIR: {ANALYSIS_DIR}")
    print(f"   VECTOR_DB_DIR: {VECTOR_DB_DIR}")
    print()
    
    # Stage 1: Raw articles from news_fetcher.py
    print("1. 📰 Raw Articles from news_fetcher.py")
    articles = load_news_articles()
    print(f"   Found: {len(articles)} articles in {OUTPUT_DIR}")
    
    # Stage 2: Analysis results
    print("\n2. 🤖 AI Analysis Results")
    if os.path.exists(ANALYSIS_DIR):
        analysis_files = [f for f in os.listdir(ANALYSIS_DIR) if f.endswith('.json')]
        print(f"   Analysis files in {ANALYSIS_DIR}: {analysis_files}")
        
        for file in analysis_files:
            filepath = os.path.join(ANALYSIS_DIR, file)
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    print(f"   {file}: {len(data)} analyzed articles")
                else:
                    print(f"   {file}: {data.get('total_articles_analyzed', 'Unknown')} articles")
    else:
        print(f"   ❌ No analysis results directory: {ANALYSIS_DIR}")
    
    # Stage 3: Vector database
    print("\n3. 🗄️  Vector Database")
    if os.path.exists(VECTOR_DB_DIR):
        # Check ChromaDB specific files
        chroma_files = os.listdir(VECTOR_DB_DIR)
        print(f"   Vector DB files in {VECTOR_DB_DIR}: {len(chroma_files)} items")
        
        # Try to load and check the vector database
        try:
            from vector_db import LangChainVectorDB
            vector_db = LangChainVectorDB()
            if vector_db.load_articles():
                stats = vector_db.get_database_stats()
                print(f"   ✅ Vector DB status: {stats['status']}")
                print(f"   📊 Documents: {stats.get('document_count', 'Unknown')}")
                print(f"   🔧 Embedding model: {stats.get('embedding_model', 'Unknown')}")
            else:
                print("   ❌ Could not load vector database")
        except Exception as e:
            print(f"   ❌ Error loading vector DB: {e}")
    else:
        print(f"   ❌ No vector database directory: {VECTOR_DB_DIR}")
    
    print("\n" + "=" * 50)
    print("💡 If any stage shows issues, run:")
    print("   python news_fetcher.py && python analysis.py")

def check_environment():
    """Check if environment variables are set correctly"""
    print("🌍 Environment Check")
    print("=" * 30)
    
    required_vars = ['OPENAI_API_KEY']
    optional_vars = ['MAX_ARTICLES_PER_SOURCE', 'MODEL', 'EMBEDDING_MODEL', 
                    'OUTPUT_DIR', 'ANALYSIS_DIR', 'VECTOR_DB_DIR']
    
    print("Required variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: Set")
        else:
            print(f"   ❌ {var}: Not set")
    
    print("\nOptional variables (using defaults if not set):")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"   ⚙️  {var}: {value} (custom)")
        else:
            default_value = globals().get(var, 'Unknown')
            print(f"   🔧 {var}: {default_value} (default)")

if __name__ == "__main__":
    check_environment()
    print()
    check_data_pipeline()
