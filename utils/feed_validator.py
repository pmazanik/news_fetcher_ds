import feedparser
from typing import List, Dict

def validate_rss_feeds(feed_urls: List[str]) -> Dict[str, bool]:
    """Validate RSS feeds and return their status"""
    results = {}
    
    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            status = feed.get('status', 0)
            entries = len(feed.entries)
            
            if status == 200 and entries > 0:
                results[feed_url] = True
                print(f"✅ {feed_url}: {entries} entries")
            else:
                results[feed_url] = False
                print(f"❌ {feed_url}: Status {status}, Entries {entries}")
                
        except Exception as e:
            results[feed_url] = False
            print(f"💥 {feed_url}: Error {e}")
    
    return results

# Test the current feeds
if __name__ == "__main__":
    test_feeds = [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://phys.org/rss-feed/breaking/",
        "https://news.mit.edu/rss/topic/science"
    ]
    
    print("🔍 Testing RSS feeds...")
    validate_rss_feeds(test_feeds)