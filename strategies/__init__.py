from strategies.rss_strategy import RSSStrategy
from strategies.web_crawler_strategy import WebCrawlerStrategy
from strategies.pdf_strategy import PDFStrategy

class StrategyFactory:
    @staticmethod
    def create_strategy(strategy_type: str, config: dict):
        strategies = {
            'rss': RSSStrategy,
            'web_crawler': WebCrawlerStrategy,
            'pdf_strategy': PDFStrategy
        }
        
        strategy_class = strategies.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_type}")
        
        return strategy_class(config)