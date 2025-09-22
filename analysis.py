#!/usr/bin/env python3
"""
News Article Analysis using OpenAI GPT models (without LangChain)
"""

import os
import json
import glob
import re
from typing import List, Dict
from dotenv import load_dotenv
import openai
from news_fetcher.config import OUTPUT_DIR

# Load environment variables
load_dotenv()

class SimpleNewsAnalyzer:
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.0):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = model_name
        self.temperature = temperature
    
    def analyze_article(self, article: Dict) -> Dict:
        """Analyze a single article using GPT"""
        try:
            prompt = f"""
Analyze this news article and provide JSON output with these exact fields:
- "summary": concise summary of main points (2-3 sentences)
- "key_topics": list of 3-5 main topics as strings
- "sentiment": one of: "positive", "negative", "neutral"
- "urgency": one of: "high", "medium", "low" 
- "key_entities": list of important people, organizations, or locations

ARTICLE TITLE: {article.get('title', 'No title')}
ARTICLE CONTENT: {article.get('text', '')[:3000]}

Return ONLY valid JSON format, no other text.
"""
            
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a news analyst. Return only valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            
            # Extract and parse JSON from response
            content = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    **analysis,
                    "original_title": article.get('title'),
                    "original_url": article.get('url'),
                    "original_source": article.get('source')
                }
            else:
                return {
                    "summary": "Analysis failed - JSON parsing error",
                    "key_topics": [],
                    "sentiment": "unknown",
                    "urgency": "unknown",
                    "key_entities": [],
                    "error": "Could not parse JSON from response"
                }
            
        except Exception as e:
            print(f"Error analyzing article: {e}")
            return {
                "summary": "Analysis failed",
                "key_topics": [],
                "sentiment": "unknown",
                "urgency": "unknown",
                "key_entities": [],
                "error": str(e)
            }

    def analyze_articles_batch(self, articles: List[Dict], max_articles: int = None) -> List[Dict]:
        """Analyze multiple articles"""
    #    if max_articles:
    #        articles = articles[:max_articles]
        
        results = []
        for i, article in enumerate(articles):
            print(f"Analyzing article {i+1}/{len(articles)}: {article.get('title', 'Unknown')[:50]}...")
            article_data = self.analyze_article(article)
            results.append(article_data)
            
            # Add delay to avoid rate limiting
            import time
            time.sleep(1)
        
        return results

def load_news_articles() -> List[Dict]:
    """Load news articles from JSON files"""
    articles = []
    
    combined_file = f"{OUTPUT_DIR}/all_news_combined.json"
    if os.path.exists(combined_file):
        with open(combined_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'articles' in data:
            articles = data['articles']
        else:
            articles = data
    
    if not articles:
        json_files = glob.glob(f"{OUTPUT_DIR}/*_news_*.json")
        for file_path in json_files:
            if 'all_news' in file_path:
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'articles' in data:
                articles.extend(data['articles'])
            else:
                articles.extend(data)
    
    return articles

def save_analysis_results(analysis_results: List[Dict], filename: str = "news_analysis.json"):
    """Save analysis results to JSON file"""
    output_dir = "analysis_results"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, filename)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    print(f"Analysis results saved to: {output_path}")
    return output_path

def generate_summary_report(analysis_results: List[Dict]):
    """Generate a summary report of all analyses"""
    summary = {
        "total_articles_analyzed": len(analysis_results),
        "sources": {},
        "common_topics": {},
        "sentiment_distribution": {},
        "urgency_distribution": {}
    }
    
    for result in analysis_results:
        source = result.get('original_source', 'unknown')
        summary['sources'][source] = summary['sources'].get(source, 0) + 1
        
        sentiment = result.get('sentiment', 'unknown')
        summary['sentiment_distribution'][sentiment] = summary['sentiment_distribution'].get(sentiment, 0) + 1
        
        urgency = result.get('urgency', 'unknown')
        summary['urgency_distribution'][urgency] = summary['urgency_distribution'].get(urgency, 0) + 1
        
        for topic in result.get('key_topics', []):
            summary['common_topics'][topic] = summary['common_topics'].get(topic, 0) + 1
    
    summary['common_topics'] = dict(sorted(
        summary['common_topics'].items(), 
        key=lambda x: x[1], 
        reverse=True
    ))
    
    return summary

def main():
    """Main analysis function"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        return
    
    print("Loading news articles...")
    articles = load_news_articles()
    
    if not articles:
        print("No articles found. Please run main.py first to fetch news.")
        return
    
    print(f"Found {len(articles)} articles for analysis")
    
    # Initialize analyzer
    analyzer = SimpleNewsAnalyzer(model_name="gpt-3.5-turbo")
    
    # Analyze articles (limit to 5 for testing)
    print("\nStarting analysis with OpenAI GPT...")
    analysis_results = analyzer.analyze_articles_batch(articles)
    
    # Save results
    output_file = save_analysis_results(analysis_results)
    
    # Generate summary report
    summary = generate_summary_report(analysis_results)
    summary_file = save_analysis_results(summary, "analysis_summary.json")
    
    print(f"\nAnalysis complete!")
    print(f"Articles analyzed: {summary['total_articles_analyzed']}")
    print(f"Sources: {summary['sources']}")
    print(f"Sentiment: {summary['sentiment_distribution']}")
    print(f"Top topics: {list(summary['common_topics'].keys())[:5]}")

if __name__ == "__main__":
    main()
