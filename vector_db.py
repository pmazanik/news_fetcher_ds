#!/usr/bin/env python3
"""
Vector database using LangChain with ChromaDB
"""

import os
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

from analysis import SimpleNewsAnalyzer, load_news_articles

from news_fetcher.config import VECTOR_DB_DIR, EMBEDDING_MODEL, MODEL

load_dotenv()

class PurePythonVectorDB:
    def __init__(self, persist_directory: str = "vector_db"):
        self.persist_directory = persist_directory or VECTOR_DB_DIR
        self.documents = []
        self.embeddings = []
        self.metadata = []
        self.embedding_model = EMBEDDING_MODEL
        self.llm_model = MODEL
        
    def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API"""
        import openai
        
        try:
            response = openai.Embedding.create(
                input=text,
                model=self.embedding_model,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        except ImportError:
            raise ImportError("LangChain dependencies not installed. Run: pip install langchain-openai")
    
    def create_documents(self, analysis_results: List[Dict]):
        """Create LangChain documents from analysis results"""
        try:
            from langchain.schema import Document
        except ImportError:
            raise ImportError("LangChain not installed. Run: pip install langchain")
        
        documents = []
        for analysis in analysis_results:
            # Create rich content for better embeddings
            content = f"""
Title: {analysis.get('original_title', 'No title')}
Source: {analysis.get('original_source', 'Unknown')}
Summary: {analysis.get('summary', 'No summary')}
Topics: {', '.join(analysis.get('key_topics', []))}
Sentiment: {analysis.get('sentiment', 'Unknown')}
Urgency: {analysis.get('urgency', 'Unknown')}
Key Entities: {', '.join(analysis.get('key_entities', []))}
"""
            
            metadata = {
                "source": analysis.get('original_source', 'Unknown'),
                "url": analysis.get('original_url', ''),
                "title": analysis.get('original_title', 'No title'),
                "sentiment": analysis.get('sentiment', 'Unknown'),
                "urgency": analysis.get('urgency', 'Unknown'),
                "topics": analysis.get('key_topics', []),
                "entities": analysis.get('key_entities', [])
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        return documents
    
    def store_articles(self, analysis_results: List[Dict]):
        """Store articles in ChromaDB using LangChain"""
        try:
            from langchain.vectorstores import Chroma
            
            documents = self.create_documents(analysis_results)
            embeddings = self._get_embeddings()
            
            # Create vector store with ChromaDB
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=self.persist_directory
            )
            
            # Create retriever for semantic search
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            print(f"✅ Stored {len(documents)} articles using {self.embedding_model}")
            return True
            
        except ImportError as e:
            print(f"❌ LangChain import error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error storing articles: {e}")
            return False
    
    def load_articles(self):
        """Load articles from persistent storage"""
        try:
            from langchain.vectorstores import Chroma
            
            if not os.path.exists(self.persist_directory):
                return False
            
            embeddings = self._get_embeddings()
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings
            )
            
            # Create retriever
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            # Get document count
            doc_count = self.vectorstore._collection.count()
            print(f"✅ Loaded {doc_count} articles from {self.persist_directory}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading articles: {e}")
            return False
    
    def semantic_search(self, query: str, k: int = 5) -> List[Dict]:
        """Perform semantic search using LangChain"""
        if not self.vectorstore:
            if not self.load_articles():
                print("❌ Vector database not initialized")
                return []
        
        try:
            results = self.vectorstore.similarity_search(query, k=k)
            return self._format_results(results)
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def _format_results(self, results) -> List[Dict]:
        """Format search results for display"""
        formatted = []
        for i, doc in enumerate(results):
            formatted.append({
                "rank": i + 1,
                "title": doc.metadata.get('title', 'No title'),
                "source": doc.metadata.get('source', 'Unknown'),
                "url": doc.metadata.get('url', ''),
                "topics": doc.metadata.get('topics', []),
                "sentiment": doc.metadata.get('sentiment', 'Unknown'),
                "similarity_score": 0.9 - (i * 0.1),  # Placeholder for actual score
                "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            })
        return formatted
    
    def create_qa_chain(self):
        """Create a question-answering chain using LangChain"""
        try:
            response = openai.ChatCompletion.create(
                model=self.llm_model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided news articles. Be concise and factual."},
                    {"role": "user", "content": f"Based on these news articles:\n\n{context}\n\nQuestion: {question}\n\nAnswer:"}
                ],
                max_tokens=500,
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
            llm = ChatOpenAI(
                model_name=self.llm_model,
                temperature=0.0,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.retriever,
                chain_type_kwargs={"prompt": PROMPT},
                return_source_documents=True
            )
            
            return qa_chain
            
        except Exception as e:
            print(f"❌ Error creating QA chain: {e}")
            return None
    
    def ask_question(self, question: str) -> Dict:
        """Ask a natural language question about the news"""
        qa_chain = self.create_qa_chain()
        if not qa_chain:
            return {"error": "QA chain not available"}
        
        try:
            result = qa_chain.invoke({"query": question})
            return {
                "answer": result['result'],
                "sources": [
                    {
                        "title": doc.metadata.get('title', 'No title'),
                        "source": doc.metadata.get('source', 'Unknown'),
                        "url": doc.metadata.get('url', '')
                    }
                    for doc in result['source_documents']
                ]
            }
        except Exception as e:
            return {"error": str(e), "answer": "Sorry, I couldn't process your question."}
    
    def get_database_stats(self) -> Dict:
        """Get statistics about the vector database"""
        if not self.vectorstore:
            return {"status": "not_initialized"}
        
        try:
            doc_count = self.vectorstore._collection.count()
            return {
                "status": "loaded",
                "document_count": doc_count,
                "persist_directory": self.persist_directory,
                "embedding_model": self.embedding_model,
                "llm_model": self.llm_model
            }
        except:
            return {"status": "error_getting_stats"}
