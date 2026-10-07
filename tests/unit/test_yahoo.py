from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.providers.yahoo import YahooProvider

YAHOO_JSON = {
    "chart": {
        "result": [
            {
                "meta": {
                    "symbol": "AAPL",
                    "regularMarketPrice": 263.85,
                    "regularMarketTime": 1791403201,
                },
                "indicators": {"quote": [{"close": [260.1, 262.4, 263.85]}]},
            }
        ],
        "error": None,
    }
}


def _mock_session(payload):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = AsyncMock(return_value=payload)

    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.get = MagicMock(return_value=mock_get)
    return mock_session


def test_yahoo_provider_init():
    provider = YahooProvider()
    assert provider.name == "yahoo"
    assert provider.api_key is None


def test_yahoo_rate_limit():
    assert YahooProvider().get_rate_limit() == 60


@pytest.mark.asyncio
async def test_yahoo_get_latest_price():
    provider = YahooProvider()
    with patch(
        "app.services.providers.yahoo.aiohttp.ClientSession",
        return_value=_mock_session(YAHOO_JSON),
    ):
        result = await provider.get_latest_price("AAPL")

    assert result["symbol"] == "AAPL"
    assert result["price"] == 263.85
    assert result["provider"] == "yahoo"
    assert "timestamp" in result
    assert "raw_response" in result


@pytest.mark.asyncio
async def test_yahoo_falls_back_to_last_close():
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "AAPL", "regularMarketTime": 1791403201},
                    "indicators": {"quote": [{"close": [260.1, 262.4]}]},
                }
            ],
            "error": None,
        }
    }
    provider = YahooProvider()
    with patch(
        "app.services.providers.yahoo.aiohttp.ClientSession",
        return_value=_mock_session(payload),
    ):
        result = await provider.get_latest_price("aapl")
    assert result["price"] == 262.4


@pytest.mark.asyncio
async def test_yahoo_no_data_raises():
    provider = YahooProvider()
    payload = {"chart": {"result": None, "error": {"description": "Not Found"}}}
    with patch(
        "app.services.providers.yahoo.aiohttp.ClientSession",
        return_value=_mock_session(payload),
    ):
        with pytest.raises(ValueError, match="No data found"):
            await provider.get_latest_price("FAKE")


@pytest.mark.asyncio
async def test_yahoo_http_error_raises():
    import aiohttp

    provider = YahooProvider()
    mock_session = _mock_session(YAHOO_JSON)
    mock_session.get.side_effect = aiohttp.ClientError("boom")
    with patch(
        "app.services.providers.yahoo.aiohttp.ClientSession",
        return_value=mock_session,
    ):
        with pytest.raises(ValueError, match="Failed to fetch data from Yahoo"):
            await provider.get_latest_price("AAPL")


def test_service_registers_yahoo_and_falls_back():
    from app.services.market_data import MarketDataService

    service = MarketDataService()
    assert "yahoo" in service.providers
    # Unknown/default provider falls back to keyless yahoo
    assert service.get_provider("nope").name == "yahoo"
    assert service.get_provider("yahoo").name == "yahoo"
