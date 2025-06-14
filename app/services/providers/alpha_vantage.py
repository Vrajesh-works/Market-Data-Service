import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Any
from .base import MarketDataProvider
from app.core.config import settings


class AlphaVantageProvider(MarketDataProvider):
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str = None):
        super().__init__(api_key or settings.ALPHA_VANTAGE_API_KEY)
        if not self.api_key:
            raise ValueError("Alpha Vantage API key is required")
    
    async def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol.upper(),
            "apikey": self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.BASE_URL, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Check for API errors
                    if "Error Message" in data:
                        raise ValueError(f"Alpha Vantage API Error: {data['Error Message']}")
                    
                    if "Note" in data:
                        raise ValueError("Alpha Vantage API rate limit exceeded")
                    
                    quote = data.get("Global Quote", {})
                    if not quote:
                        raise ValueError(f"No data found for symbol {symbol}")
                    
                    price = float(quote.get("05. price", 0))
                    timestamp = datetime.now() 
                    
                    return self.format_response(
                        symbol=symbol,
                        price=price,
                        timestamp=timestamp,
                        raw_response=data
                    )
                    
            except aiohttp.ClientError as e:
                raise ValueError(f"Failed to fetch data from Alpha Vantage: {str(e)}")
            except Exception as e:
                raise ValueError(f"Unexpected error: {str(e)}")
    
    def get_rate_limit(self) -> int:
        return 5