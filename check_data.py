#!/usr/bin/env python3
"""
Diagnostic script to check data at each stage
"""

import json
import os
from analysis import load_news_articles

def check_data_pipeline():
    """Check data at each stage of the pipeline"""
    print("🔍 Data Pipeline Diagnostic")
    print("=" * 40)
    
    # Stage 1: Raw articles from main.py
    print("1. 📰 Raw Articles from main.py")
    articles = load_news_articles()
    print(f"   Found: {len(articles)} articles")
    
    # Stage 2: Analysis results
    print("\n2. 🤖 AI Analysis Results")
    analysis_dir = "analysis_results"
    if os.path.exists(analysis_dir):
        analysis_files = [f for f in os.listdir(analysis_dir) if f.endswith('.json')]
        print(f"   Analysis files: {analysis_files}")
        
        for file in analysis_files:
            filepath = os.path.join(analysis_dir, file)
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    print(f"   {file}: {len(data)} analyzed articles")
                else:
                    print(f"   {file}: {data.get('total_articles_analyzed', 'Unknown')} articles")
    else:
        print("   ❌ No analysis results directory")
    
    # Stage 3: Vector database
    print("\n3. 🗄️  Vector Database")
    vector_dir = "vector_db"
    if os.path.exists(vector_dir):
        vector_file = os.path.join(vector_dir, "data.json")
        if os.path.exists(vector_file):
            with open(vector_file, 'r') as f:
                vector_data = json.load(f)
                if 'embeddings' in vector_data:
                    print(f"   Embeddings: {len(vector_data['embeddings'])} vectors")
                else:
                    print("   ❌ No embeddings in vector database")
        else:
            print("   ❌ No vector database file found")
    else:
        print("   ❌ No vector database directory")
    
    print("\n" + "=" * 40)
    print("💡 If any stage shows 0 items, run:")
    print("   python main.py && python analysis.py")

if __name__ == "__main__":
    check_data_pipeline()
