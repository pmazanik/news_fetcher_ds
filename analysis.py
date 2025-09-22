#!/usr/bin/env python3
"""
News Article Analysis using LangChain and OpenAI GPT models
"""

import os
import json
import glob
from typing import List, Dict
from dotenv import load_dotenv
from news_fetcher.config import OUTPUT_DIR, ANALYSIS_DIR, MODEL

load_dotenv()

class LangChainNewsAnalyzer:
    def __init__(self, model_name: str = None, temperature: float = 0.0):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required")
        
        self.model_name = model_name or MODEL
        self.temperature = temperature
    
    def analyze_article(self, article: Dict) -> Dict:
        """Analyze a single article using LangChain and OpenAI"""
        try:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage, SystemMessage
            from langchain.output_parsers import StructuredOutputParser, ResponseSchema
            import re
            
            # Define output schema
            response_schemas = [
                ResponseSchema(name="summary", description="Concise 2-3 sentence summary of main points"),
                ResponseSchema(name="key_topics", description="List of 3-5 main topics as strings"),
                ResponseSchema(name="sentiment", description="One of: positive, negative, neutral"),
                ResponseSchema(name="urgency", description="One of: high, medium, low"),
                ResponseSchema(name="key_entities", description="List of important people, organizations, locations")
            ]
            
            output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
            format_instructions = output_parser.get_format_instructions()
            
            # Create prompt
            prompt = f"""
Analyze this news article and provide structured insights:

ARTICLE TITLE: {article.get('title', 'No title')}
ARTICLE CONTENT: {article.get('text', '')[:3000]}

Please analyze this article and provide:
{format_instructions}

Keep the summary concise but comprehensive. Focus on factual accuracy.
"""
            
            # Initialize LLM
            llm = ChatOpenAI(
                model_name=self.model_name,
                temperature=self.temperature,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # Get response
            messages = [
                SystemMessage(content="You are a news analyst. Provide structured JSON output."),
                HumanMessage(content=prompt)
            ]
            
            response = llm.invoke(messages)
            
            # Parse the response
            try:
                parsed_output = output_parser.parse(response.content)
            except:
                # Fallback: try to extract JSON manually
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    parsed_output = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse JSON from response")
            
            return {
                **parsed_output,
                "original_title": article.get('title'),
                "original_url": article.get('url'),
                "original_source": article.get('source')
            }
            
        except Exception as e:
            print(f"Error analyzing article: {e}")
            return {
                "summary": f"Analysis failed: {str(e)}",
                "key_topics": [],
                "sentiment": "unknown",
                "urgency": "unknown",
                "key_entities": [],
                "error": str(e)
            }

    def analyze_articles_batch(self, articles: List[Dict], max_articles: int = None) -> List[Dict]:
        """Analyze multiple articles with progress tracking"""
        if max_articles:
            articles = articles[:max_articles]
        
        results = []
        total = len(articles)
        
        print(f"🔄 Analyzing {total} articles with {self.model_name}...")
        
        for i, article in enumerate(articles):
            print(f"   Article {i+1}/{total}: {article.get('title', 'Unknown')[:50]}...")
            article_data = self.analyze_article(article)
            results.append(article_data)
            
            # Add delay to avoid rate limiting
            import time
            time.sleep(1)
        
        return results

def main():
    """Main analysis function using LangChain"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Please create a .env file with your API key")
        return
    
    print("Loading news articles...")
    articles = load_news_articles()
    
    if not articles:
        print("No articles found. Please run news_fetcher.py first.")
        return
    
    print(f"Found {len(articles)} articles for analysis")
    
    # Initialize LangChain analyzer
    try:
        analyzer = LangChainNewsAnalyzer()
    except ImportError:
        print("❌ LangChain not installed. Run: pip install langchain-openai")
        return
    
    # Analyze articles
    print(f"\nStarting analysis with {analyzer.model_name}...")
    analysis_results = analyzer.analyze_articles_batch(articles)
    
    # Save results
    output_file = save_analysis_results(analysis_results)
    
    # Store in vector database
    try:
        from vector_db import LangChainVectorDB
        vector_db = LangChainVectorDB()
        storage_success = vector_db.store_articles(analysis_results)
        
        if storage_success:
            print("✅ Articles stored in LangChain vector database")
        else:
            print("❌ Failed to store articles in vector database")
    except ImportError:
        print("❌ LangChain vector database not available")
    
    # Generate summary report
    summary = generate_summary_report(analysis_results)
    summary_file = save_analysis_results(summary, "analysis_summary.json")
    
    print(f"\nAnalysis complete!")
    print(f"Articles analyzed: {summary['total_articles_analyzed']}")
    print(f"Sources: {summary['sources']}")

def load_news_articles() -> List[Dict]:
    """Load news articles from JSON files"""
    from news_fetcher.config import OUTPUT_DIR
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
    from news_fetcher.config import ANALYSIS_DIR
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    
    output_path = os.path.join(ANALYSIS_DIR, filename)
    
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

if __name__ == "__main__":
    main()
