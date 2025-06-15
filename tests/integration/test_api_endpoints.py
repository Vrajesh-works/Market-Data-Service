import pytest
from fastapi import status
from app.main import app
from app.api.dependencies import get_market_data_service


def test_health_endpoint(client):

    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert "status" in response.json()
    assert "service" in response.json()
    assert "version" in response.json()
    assert "database" in response.json()
    assert "components" in response.json()


def test_database_health_endpoint(client):
    response = client.get("/health/database")
    assert response.status_code == status.HTTP_200_OK
    assert "status" in response.json()
    assert "database" in response.json()


def test_get_latest_price(client, mock_market_data_service):
    # Override the market data service dependency
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service
    
    response = client.get("/api/v1/prices/latest?symbol=AAPL")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["symbol"] == "AAPL"
    assert response.json()["price"] == 150.25
    assert "timestamp" in response.json()
    assert response.json()["provider"] == "alpha_vantage"
    
    # Test with invalid symbol
    mock_market_data_service.get_latest_price.side_effect = ValueError("Invalid symbol")
    response = client.get("/api/v1/prices/latest?symbol=INVALID")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    # Reset the side effect
    mock_market_data_service.get_latest_price.side_effect = None
    
    # Clean up the override
    app.dependency_overrides = {}


def test_get_price_history(client, mock_market_data_service):
    # Override the market data service dependency
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service
    
    response = client.get("/api/v1/prices/history/AAPL?hours=24")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2
    assert response.json()[0]["symbol"] == "AAPL"
    assert response.json()[0]["price"] == 150.25
    
    mock_market_data_service.get_price_history.side_effect = ValueError("Invalid symbol")
    response = client.get("/api/v1/prices/history/INVALID?hours=24")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    mock_market_data_service.get_price_history.side_effect = None
    
    app.dependency_overrides = {}


def test_get_moving_average(client, mock_market_data_service):
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service
    
    response = client.get("/api/v1/prices/moving-average/AAPL?period=5")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["symbol"] == "AAPL"
    assert response.json()["moving_average"] == 150.0
    assert response.json()["period"] == 5
    assert "timestamp" in response.json()
    
    mock_market_data_service.get_moving_average.side_effect = ValueError("Invalid symbol")
    response = client.get("/api/v1/prices/moving-average/INVALID?period=5")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    mock_market_data_service.get_moving_average.side_effect = None
    
    app.dependency_overrides = {}


def test_start_polling_job(client, mock_market_data_service, sample_poll_request):
    app.dependency_overrides[get_market_data_service] = lambda: mock_market_data_service
    
    response = client.post("/api/v1/prices/poll", json=sample_poll_request)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["job_id"] == "poll_12345678"
    assert response.json()["status"] == "accepted"
    assert "config" in response.json()
    assert response.json()["config"]["symbols"] == sample_poll_request["symbols"]
    assert response.json()["config"]["interval"] == sample_poll_request["interval"]
    
    mock_market_data_service.start_polling_job.side_effect = ValueError("Invalid request")
    response = client.post("/api/v1/prices/poll", json={"invalid": "request"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    mock_market_data_service.start_polling_job.side_effect = None
    
    app.dependency_overrides = {} 