from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import json

@dataclass
class NewsArticle:
    source: str
    title: str
    content: str
    url: str
    published_date: Optional[datetime]
    category: str
    summary: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return {
            'source': self.source,
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'category': self.category,
            'summary': self.summary,
            'metadata': self.metadata or {},
            'content_length': len(self.content),
            'word_count': len(self.content.split())
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)