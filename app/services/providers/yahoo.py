import logging
from datetime import datetime
from typing import Any, Dict

import aiohttp

from .base import MarketDataProvider

logger = logging.getLogger(__name__)


class YahooProvider(MarketDataProvider):
    """Free, keyless market data from Yahoo Finance's public chart API.

    No API key required, which makes it the default provider for
    demos and deployments where no Alpha Vantage key is configured.
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )

    def __init__(self, api_key: str = None):
        # Yahoo needs no key; accept and ignore one for interface parity.
        super().__init__(api_key)
        self.name = "yahoo"

    async def get_latest_price(self, symbol: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{symbol.upper()}"
        params = {"interval": "1d", "range": "5d"}
        headers = {"User-Agent": self.USER_AGENT}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
            except aiohttp.ClientError as e:
                raise ValueError(f"Failed to fetch data from Yahoo Finance: {e}")

        results = (data.get("chart") or {}).get("result") or []
        if not results:
            error = (data.get("chart") or {}).get("error") or {}
            raise ValueError(
                f"No data found for symbol {symbol}: "
                f"{error.get('description', 'unknown error')}"
            )

        meta = results[0].get("meta") or {}
        price = meta.get("regularMarketPrice") or self._last_close(results[0])
        if not price or price <= 0:
            raise ValueError(f"No price data found for symbol {symbol}")

        ts = meta.get("regularMarketTime")
        timestamp = datetime.fromtimestamp(ts) if ts else datetime.now()

        return self.format_response(
            symbol=symbol,
            price=float(price),
            timestamp=timestamp,
            raw_response={"provider": "yahoo", "meta": meta},
        )

    @staticmethod
    def _last_close(result: Dict[str, Any]):
        quotes = (result.get("indicators") or {}).get("quote") or [{}]
        closes = [c for c in (quotes[0].get("close") or []) if c]
        return closes[-1] if closes else None

    def get_rate_limit(self) -> int:
        # Yahoo publishes no hard limit; stay polite.
        return 60
