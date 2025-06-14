from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class MarketDataProvider(ABC):
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.name = self.__class__.__name__.lower().replace('provider', '')
    
    @abstractmethod
    async def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        #Fetch the latest price for a given symbol
        
        pass
    
    @abstractmethod
    def get_rate_limit(self) -> int:
        pass
    
    def format_response(self, symbol: str, price: float, timestamp: datetime, 
                       raw_response: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "symbol": symbol.upper(),
            "price": price,
            "timestamp": timestamp,
            "provider": self.name,
            "raw_response": raw_response
        }