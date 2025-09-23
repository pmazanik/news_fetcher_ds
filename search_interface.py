#!/usr/bin/env python3
"""
Search interface using LangChain for semantic search
"""

import json

from vector_db import PurePythonVectorDB
from analysis import load_news_articles, SimpleNewsAnalyzer

from news_fetcher.config import MODEL, EMBEDDING_MODEL, VECTOR_DB_DIR

class LangChainSearchEngine:
    def __init__(self):
        self.vector_db = LangChainVectorDB()
        self.analyzer = LangChainNewsAnalyzer()

    def initialize_database(self):
        """Initialize the vector database with news articles"""
        print("📂 Loading news articles...")
        articles = load_news_articles()

        if not articles:
            print("❌ No articles found. Please run news_fetcher.py first.")
            return False

        print(f"📊 Found {len(articles)} articles.")
        print(f"🔧 Configuration - Model: {MODEL}, Embedding: {EMBEDDING_MODEL}")

        # First try to load existing analysis to save time and API calls

        try:
            if self.vector_db.load_articles():
                stats = self.vector_db.get_database_stats()
                print(f"✅ Loaded existing database from {VECTOR_DB_DIR}")
                print(f"   Documents: {stats.get('document_count', 0)} articles")
                return True
        except Exception as e:
            print(f"ℹ️  No existing data found ({e}), analyzing fresh...")

        print("🔄 Analyzing articles with LangChain...")

        # Analyze ALL articles
        analysis_results = self.analyzer.analyze_articles_batch(articles)

        # Store in vector database
        success = self.vector_db.store_articles(analysis_results)

        if success:
            print(f"✅ Database initialized with {len(analysis_results)} articles!")
            print(f"💾 Saved to: {VECTOR_DB_DIR}")
            return True
        else:
            print("❌ Failed to initialize database")
            return False
    
    def search_news(self, query: str, top_k: int = 5):
        """Search for news articles using semantic search"""
        print(f"\n🔍 Semantic search for: '{query}'")
        print("=" * 60)
        
        results = self.vector_db.semantic_search(query, k=top_k)
        
        if not results:
            print("❌ No results found.")
            return
        
        print(f"✅ Found {len(results)} relevant articles:\n")
        
        for result in results:
            print(f"📰 {result['title']} (similarity: {result['similarity']:.3f})")
            print(f"   Source: {result['source']}")
            if result['topics']:
                print(f"   Topics: {', '.join(result['topics'][:3])}")
            print(f"   URL: {result['url']}")
            print(f"   Snippet: {result['snippet']}")
            print("-" * 60)
    
    def ask_news_question(self, question: str):
        """Ask a natural language question about the news"""
        print(f"\n❓ Question: {question}")
        print("=" * 50)
        
        answer = self.vector_db.ask_question(question)
        
        if 'error' in answer:
            print(f"❌ Error: {answer['error']}")
            return
        
        print(f"🤖 Answer: {answer['answer']}\n")
        
        if answer.get('sources'):
            print("📚 Sources:")
            for source in answer['sources']:
                print(f"   - {source['title']} ({source['source']})")
    
    def show_database_stats(self):
        """Show statistics about the loaded database"""
        print("\n📊 Database Statistics")
        print("=" * 30)
        
        if hasattr(self.vector_db, 'embeddings') and self.vector_db.embeddings:
            print(f"Articles loaded: {len(self.vector_db.embeddings)}")
        elif hasattr(self.vector_db, 'documents') and self.vector_db.documents:
            print(f"Articles loaded: {len(self.vector_db.documents)}")
        else:
            print("No articles loaded - database not initialized")
    
    def interactive_search(self):
        """Start interactive search session"""
        print("🎯 Pure Python News Search Engine")
        print("=" * 50)
        
        # Show database stats first
        self.show_database_stats()
        
        print("\nCommands:")
        print("  /search [query]    - Semantic search for articles")
        print("  /ask [question]    - Ask a natural language question")
        print("  /stats             - Show database statistics")
        print("  /quit              - Exit the search interface")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\n💬 Enter command: ").strip()
                
                if user_input.lower() in ['/quit', 'quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                elif user_input.startswith('/search '):
                    query = user_input[8:].strip()
                    if query:
                        self.search_news(query)
                    else:
                        print("❌ Please provide a search query.")
                
                elif user_input.startswith('/ask '):
                    question = user_input[5:].strip()
                    if question:
                        self.ask_news_question(question)
                    else:
                        print("❌ Please provide a question.")
                
                elif user_input in ['/stats', 'stats']:
                    self.show_database_stats()
                
                elif user_input in ['/help', 'help', '?']:
                    print("📋 Available commands:")
                    print("  /search [query]    - Find relevant articles")
                    print("  /ask [question]    - Ask a question about the news")
                    print("  /stats             - Show database information")
                    print("  /quit              - Exit the search interface")
                
                else:
                    print("❌ Unknown command. Type /help for available commands.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    """Main function"""
    search_engine = PurePythonSearchEngine()
    
    print("🚀 Initializing pure Python vector database...")
    if search_engine.initialize_database():
        search_engine.interactive_search()
    else:
        print("❌ Failed to initialize search engine")

if __name__ == "__main__":
    main()
