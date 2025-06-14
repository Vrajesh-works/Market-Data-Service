from fastapi import Depends, HTTPException, status
from app.core.config import settings
from app.services.market_data import market_data_service, MarketDataService


def get_settings():
    return settings


def get_market_data_service() -> MarketDataService:
    return market_data_service


def validate_symbol(symbol: str) -> str:
    if not symbol or len(symbol) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Symbol must be between 1 and 10 characters"
        )
    return symbol.upper().strip()


def validate_provider(provider: str = None) -> str:
    if provider and provider not in ["alpha_vantage", "yahoo", "finnhub"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider. Supported: alpha_vantage, yahoo, finnhub"
        )
    return provider