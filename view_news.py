#!/usr/bin/env python3
"""
Script to view and analyze fetched news data
"""

import json
import os
import glob
from datetime import datetime
from news_fetcher.config import OUTPUT_DIR

def view_latest_news():
    """View the latest fetched news"""
    if not os.path.exists(OUTPUT_DIR):
        print("No news data found. Run main.py first.")
        return
    
    # Find all JSON files
    json_files = glob.glob(f"{OUTPUT_DIR}/*.json")
    if not json_files:
        print("No JSON files found in news_data/")
        return
    
    # Try to find the combined file first
    combined_file = f"{OUTPUT_DIR}/all_news_combined.json"
    if os.path.exists(combined_file):
        try:
            with open(combined_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it's the new format with metadata
            if isinstance(data, dict) and 'articles' in data:
                articles = data['articles']
                metadata = data.get('metadata', {})
                print(f"Latest News Summary ({len(articles)} articles)")
                print(f"Generated: {metadata.get('generated_at', 'Unknown')}")
                print("=" * 60)
                
                sources = {}
                for article in articles:
                    source = article.get('source', 'Unknown')
                    sources[source] = sources.get(source, 0) + 1
                
                for source, count in sources.items():
                    print(f"{source}: {count} articles")
                
                # Show sample articles
                print(f"\nSample Articles:")
                for i, article in enumerate(articles[:5]):
                    print(f"\n{i+1}. {article.get('source', 'Unknown')}")
                    print(f"   Title: {article.get('title', 'No title')[:80]}...")
                    print(f"   URL: {article.get('url', 'No URL')}")
                    print(f"   Date: {article.get('publish_date', 'Unknown')}")
                    if article.get('authors'):
                        print(f"   Authors: {', '.join(article['authors'])}")
                    print(f"   Text length: {len(article.get('text', ''))} chars")
            
            else:
                # Old format - direct list of articles
                print(f"Latest News Summary ({len(data)} articles)")
                print("=" * 50)
                
                sources = {}
                for article in data:
                    source = article.get('source', 'Unknown')
                    sources[source] = sources.get(source, 0) + 1
                
                for source, count in sources.items():
                    print(f"{source}: {count} articles")
                    
        except Exception as e:
            print(f"Error reading combined file: {e}")
    else:
        print("No combined news file found. Checking individual source files...")
        view_individual_sources()

def view_individual_sources():
    """View individual source files"""
    source_files = glob.glob(f"{OUTPUT_DIR}/*_news_*.json")
    source_files = [f for f in source_files if 'all_news' not in f]
    
    if not source_files:
        print("No individual source files found.")
        return
    
    print("\nIndividual Source Files:")
    print("=" * 40)
    
    for file_path in source_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            filename = os.path.basename(file_path)
            
            if isinstance(data, dict) and 'articles' in data:
                articles = data['articles']
                metadata = data.get('metadata', {})
                print(f"\n{filename}:")
                print(f"  Source: {metadata.get('source', 'Unknown')}")
                print(f"  Articles: {len(articles)}")
                print(f"  Generated: {metadata.get('generated_at', 'Unknown')}")
                
            elif isinstance(data, list):
                print(f"\n{filename}:")
                print(f"  Articles: {len(data)}")
                sources = {}
                for article in data:
                    source = article.get('source', 'Unknown')
                    sources[source] = sources.get(source, 0) + 1
                for source, count in sources.items():
                    print(f"  Source: {source} ({count} articles)")
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

def show_file_stats():
    """Show statistics about the data files"""
    if not os.path.exists(OUTPUT_DIR):
        return
    
    json_files = glob.glob(f"{OUTPUT_DIR}/*.json")
    print(f"\nFile Statistics:")
    print(f"Total JSON files: {len(json_files)}")
    
    for file_path in json_files:
        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            print(f"  {filename}: {file_size / 1024:.1f} KB")
        except:
            pass

if __name__ == "__main__":
    print("News Data Viewer")
    print("=" * 40)
    view_latest_news()
    show_file_stats()
