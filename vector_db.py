#!/usr/bin/env python3
"""
Pure Python vector store using OpenAI embeddings and cosine similarity
"""

import os
import json
import numpy as np
from typing import List, Dict
from dotenv import load_dotenv
from analysis import SimpleNewsAnalyzer, load_news_articles

load_dotenv()

class PurePythonVectorDB:
    def __init__(self, persist_directory: str = "vector_db"):
        self.persist_directory = persist_directory
        self.documents = []
        self.embeddings = []
        self.metadata = []
        
    def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API"""
        import openai
        
        try:
            response = openai.Embedding.create(
                input=text,
                model="text-embedding-ada-002",
                api_key=os.getenv("OPENAI_API_KEY")
            )
            return response['data'][0]['embedding']
        except Exception as e:
            print(f"❌ Error getting embedding: {e}")
            return [0.0] * 1536  # Return zero vector as fallback
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def create_documents(self, analysis_results: List[Dict]):
        """Create document representations"""
        documents = []
        for analysis in analysis_results:
            content = f"""
Title: {analysis.get('original_title', 'No title')}
Summary: {analysis.get('summary', 'No summary')}
Topics: {', '.join(analysis.get('key_topics', []))}
Source: {analysis.get('original_source', 'Unknown')}
"""
            
            metadata = {
                "source": analysis.get('original_source', 'Unknown'),
                "url": analysis.get('original_url', ''),
                "title": analysis.get('original_title', 'No title'),
                "topics": analysis.get('key_topics', [])
            }
            
            documents.append({
                "content": content,
                "metadata": metadata
            })
        
        return documents
    
    def store_articles(self, analysis_results: List[Dict]):
        """Store articles with OpenAI embeddings"""
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OPENAI_API_KEY required")
            return False
        
        self.documents = self.create_documents(analysis_results)
        self.embeddings = []
        self.metadata = []
        
        print("🔄 Generating embeddings...")
        for i, doc in enumerate(self.documents):
            print(f"   Embedding document {i+1}/{len(self.documents)}")
            embedding = self._get_openai_embedding(doc["content"])
            self.embeddings.append(embedding)
            self.metadata.append(doc["metadata"])
            
            # Add small delay to avoid rate limiting
            import time
            time.sleep(0.1)
        
        # Save to disk
        os.makedirs(self.persist_directory, exist_ok=True)
        self._save_to_disk()
        
        print(f"✅ Stored {len(self.documents)} articles with embeddings")
        return True
    
    def _save_to_disk(self):
        """Save data to disk"""
        data = {
            "embeddings": self.embeddings,
            "metadata": self.metadata,
            "documents": [doc["content"] for doc in self.documents]
        }
        
        with open(os.path.join(self.persist_directory, "data.json"), "w") as f:
            json.dump(data, f)
    
    def load_from_disk(self):
        """Load data from disk"""
        try:
            with open(os.path.join(self.persist_directory, "data.json"), "r") as f:
                data = json.load(f)
            
            self.embeddings = data["embeddings"]
            self.metadata = data["metadata"]
            self.documents = [{"content": content} for content in data["documents"]]
            
            print("✅ Loaded articles from disk")
            return True
        except:
            print("❌ No saved data found")
            return False
    
    def semantic_search(self, query: str, k: int = 5) -> List[Dict]:
        """Perform semantic search using cosine similarity"""
        if not self.embeddings:
            if not self.load_from_disk():
                print("❌ No data available for search")
                return []
        
        # Get query embedding
        query_embedding = self._get_openai_embedding(query)
        
        # Calculate similarities
        similarities = []
        for i, doc_embedding in enumerate(self.embeddings):
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            similarities.append((i, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        results = []
        for i, (doc_idx, similarity) in enumerate(similarities[:k]):
            metadata = self.metadata[doc_idx]
            content = self.documents[doc_idx]["content"]
            
            results.append({
                "rank": i + 1,
                "title": metadata.get('title', 'No title'),
                "source": metadata.get('source', 'Unknown'),
                "url": metadata.get('url', ''),
                "topics": metadata.get('topics', []),
                "similarity": float(similarity),
                "snippet": content[:200] + "..." if len(content) > 200 else content
            })
        
        return results
    
    def ask_question(self, question: str) -> Dict:
        """Simple question answering using search results"""
        # First, find relevant articles
        results = self.semantic_search(question, k=3)
        
        if not results:
            return {"answer": "I couldn't find relevant information to answer your question."}
        
        # Create context from top results
        context = "\n\n".join([
            f"Article {i+1}: {result['title']} ({result['source']})\n{result['snippet']}"
            for i, result in enumerate(results)
        ])
        
        # Use OpenAI to generate answer
        import openai
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided news articles. Be concise and factual."},
                    {"role": "user", "content": f"Based on these news articles:\n\n{context}\n\nQuestion: {question}\n\nAnswer:"}
                ],
                max_tokens=500,
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
            return {
                "answer": response.choices[0].message.content,
                "sources": [
                    {
                        "title": result['title'],
                        "source": result['source'],
                        "url": result['url']
                    }
                    for result in results
                ]
            }
            
        except Exception as e:
            return {"error": str(e), "answer": "Sorry, I couldn't generate an answer."}
