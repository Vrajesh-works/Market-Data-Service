import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import get_db, db_manager
from app.models.database import Base
from app.services.market_data import MarketDataService
from app.services.providers.alpha_vantage import AlphaVantageProvider


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Override the get_db dependency
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestingSessionLocal()


@pytest.fixture
def client(test_db):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_alpha_vantage():
    mock_provider = MagicMock(spec=AlphaVantageProvider)
    mock_provider.name = "alpha_vantage"
    mock_provider.get_latest_price.return_value = {
        "symbol": "AAPL",
        "price": 150.25,
        "timestamp": "2024-03-20T10:30:00Z",
        "provider": "alpha_vantage",
        "raw_response": {"Global Quote": {"05. price": "150.25"}}
    }
    return mock_provider


@pytest.fixture
def mock_market_data_service(mock_alpha_vantage):
    mock_service = MagicMock(spec=MarketDataService)
    mock_service.get_provider.return_value = mock_alpha_vantage
    mock_service.get_latest_price.return_value = {
        "symbol": "AAPL",
        "price": 150.25,
        "timestamp": "2024-03-20T10:30:00Z",
        "provider": "alpha_vantage",
        "source": "live"
    }
    mock_service.get_price_history.return_value = [
        {
            "symbol": "AAPL",
            "price": 150.25,
            "timestamp": "2024-03-20T10:30:00Z",
            "provider": "alpha_vantage"
        },
        {
            "symbol": "AAPL",
            "price": 149.80,
            "timestamp": "2024-03-20T10:25:00Z",
            "provider": "alpha_vantage"
        }
    ]
    mock_service.get_moving_average.return_value = {
        "symbol": "AAPL",
        "moving_average": 150.0,
        "period": 5,
        "timestamp": "2024-03-20T10:30:00Z"
    }
    mock_service.start_polling_job.return_value = "poll_12345678"
    return mock_service


@pytest.fixture
def sample_price_data():
    return {
        "symbol": "AAPL",
        "price": 150.25,
        "timestamp": "2024-03-20T10:30:00Z",
        "provider": "alpha_vantage"
    }


@pytest.fixture
def sample_poll_request():
    return {
        "symbols": ["AAPL", "MSFT"],
        "interval": 60,
        "provider": "alpha_vantage"
    } 