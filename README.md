[200~# News Fetcher Project

A Python application that fetches the latest news articles from major news sources and stores them in JSON format with full text content.

## Features

- Fetches news from 4 major sources: BBC, CNN, The Guardian, and AP News
- Extracts full article text using newspaper3k library
- Saves data in structured JSON format with metadata
- Multi-threaded fetching with proper rate limiting
- Comprehensive error handling and logging

## Project Structure
news_fetcher/
├── news_fetcher/
│ ├── init.py
│ ├── config.py
│ ├── utils.py
│ └── fetchers.py
├── requirements.txt
├── main.py
├── view_news.py
├── README.md
└── news_data/ (generated directory)


## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt

Usage
Run the main script to fetch news:

python main.py

python view_news.py

Output Format
The application generates JSON files in the news_data/ directory with the following structure:

{
  "metadata": {
    "generated_at": "2023-12-07T10:30:00",
    "total_articles": 20,
    "source": "BBC",
    "version": "1.0"
  },
  "articles": [
    {
      "title": "Article Title",
      "text": "Full article content...",
      "publish_date": "2023-12-07T08:00:00",
      "authors": ["Author Name"],
      "url": "https://example.com/article",
      "source": "BBC",
      "summary": "Article summary..."
    }
  ]
}

News Sources
BBC: World news and current affairs (RSS: https://feeds.bbci.co.uk/news/rss.xml)

CNN: Breaking news and international coverage (RSS: http://rss.cnn.com/rss/edition.rss)

The Guardian: International journalism (RSS: https://www.theguardian.com/world/rss)

AP News: Associated Press global news (RSS: https://apnews.com/feed)

Dependencies
requests==2.31.0

beautifulsoup4==4.12.2

newspaper3k==0.2.8

lxml==4.9.3

feedparser==6.0.10

tqdm==4.66.1

python-dateutil==2.8.2

Logging
Detailed logs are saved to news_fetcher.log for debugging and monitoring purposes.


## view_news.py (for examining data)

```python
#!/usr/bin/env python3
"""
Script to view and analyze fetched news data
"""

import json
import os
from datetime import datetime
from news_fetcher.config import OUTPUT_DIR

def view_latest_news():
    """View the latest fetched news"""
    if not os.path.exists(OUTPUT_DIR):
        print("No news data found. Run main.py first.")
        return
    
    # Find latest combined file
    json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
    if not json_files:
        print("No JSON files found in news_data/")
        return
    
    combined_file = f"{OUTPUT_DIR}/all_news_combined.json"
    if os.path.exists(combined_file):
        with open(combined_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Latest News Summary ({len(data['articles'])} articles)")
        print("=" * 50)
        
        sources = {}
        for article in data['articles']:
            source = article['source']
            sources[source] = sources.get(source, 0) + 1
        
        for source, count in sources.items():
            print(f"{source}: {count} articles")
        
        # Show sample articles
        print(f"\nSample Articles:")
        for i, article in enumerate(data['articles'][:3]):
            print(f"\n{i+1}. {article['source']} - {article['title'][:70]}...")
            print(f"   URL: {article['url']}")
            print(f"   Date: {article.get('publish_date', 'Unknown')}")
            if article.get('authors'):
                print(f"   Authors: {', '.join(article['authors'])}")
    
    else:
        print("No combined news file found.")

if __name__ == "__main__":
    print("News Data Viewer")
    print("=" * 30)
    view_latest_news()
