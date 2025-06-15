import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp
from app.services.providers.alpha_vantage import AlphaVantageProvider
from app.services.providers.base import MarketDataProvider


def test_base_provider_interface():

    with pytest.raises(TypeError):
        provider = MarketDataProvider()


def test_alpha_vantage_provider_init():

    provider = AlphaVantageProvider(api_key="test_key")
    assert provider.api_key == "test_key"
    assert provider.name == "alpha_vantage"
    
    with patch("app.services.providers.alpha_vantage.settings") as mock_settings:
        mock_settings.ALPHA_VANTAGE_API_KEY = "settings_key"
        provider = AlphaVantageProvider()
        assert provider.api_key == "settings_key"
    
    with pytest.raises(ValueError):
        provider = AlphaVantageProvider(api_key="")


@pytest.mark.asyncio
async def test_alpha_vantage_get_latest_price():
    """Test the Alpha Vantage get_latest_price method"""
    provider = AlphaVantageProvider(api_key="test_key")
    
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={
        "Global Quote": {
            "01. symbol": "AAPL",
            "05. price": "150.25",
            "07. latest trading day": "2024-03-20"
        }
    })
    
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = AsyncMock(return_value=mock_response)
    
    with patch("app.services.providers.alpha_vantage.aiohttp.ClientSession", return_value=mock_session):
        result = await provider.get_latest_price("AAPL")
        
        assert result["symbol"] == "AAPL"
        assert result["price"] == 150.25
        assert "timestamp" in result
        assert result["provider"] == "alpha_vantage"
        assert "raw_response" in result


@pytest.mark.asyncio
async def test_alpha_vantage_error_handling():
    """Test error handling in the Alpha Vantage provider"""
    provider = AlphaVantageProvider(api_key="test_key")
    
    # Test API error response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value={
        "Error Message": "Invalid API call"
    })
    
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = AsyncMock(return_value=mock_response)
    
    with patch("app.services.providers.alpha_vantage.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(ValueError, match="Alpha Vantage API Error"):
            await provider.get_latest_price("AAPL")
    
    # Test rate limit exceeded
    mock_response.json = AsyncMock(return_value={
        "Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 5 requests per minute and 500 requests per day."
    })
    
    with patch("app.services.providers.alpha_vantage.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(ValueError, match="Alpha Vantage API rate limit exceeded"):
            await provider.get_latest_price("AAPL")
    
    # Test HTTP error
    mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientError("HTTP Error"))
    
    with patch("app.services.providers.alpha_vantage.aiohttp.ClientSession", return_value=mock_session):
        with pytest.raises(ValueError, match="Failed to fetch data from Alpha Vantage"):
            await provider.get_latest_price("AAPL")


def test_alpha_vantage_rate_limit():
    """Test the Alpha Vantage rate limit method"""
    provider = AlphaVantageProvider(api_key="test_key")
    assert provider.get_rate_limit() == 5 