import pytest
import requests
import time
import os
from datetime import datetime, timedelta


# Skip these tests if we're not running in an environment with the full stack
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_E2E_TESTS") != "1",
    reason="End-to-end tests require the full stack to be running"
)

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")


def test_e2e_price_pipeline():

    # 1. Health check to ensure the service is running
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
    # 2. Get latest price (stores in DB)
    response = requests.get(f"{BASE_URL}/api/v1/prices/latest?symbol=AAPL")
    assert response.status_code == 200
    price_data = response.json()
    assert price_data["symbol"] == "AAPL"
    assert isinstance(price_data["price"], float)
    assert "timestamp" in price_data
    
    # 3. Get price history to verify storage
    response = requests.get(f"{BASE_URL}/api/v1/prices/history/AAPL?hours=1")
    assert response.status_code == 200
    history = response.json()
    assert len(history) > 0
    
    # 4. Get more price points to ensure we have enough for moving average
    for _ in range(4):
        response = requests.get(f"{BASE_URL}/api/v1/prices/latest?symbol=AAPL&use_cache=false")
        assert response.status_code == 200
        time.sleep(1)
    
    # 5. Wait for the Kafka consumer to process the events
    time.sleep(5)
    
    # 6. Check that the moving average is calculated
    response = requests.get(f"{BASE_URL}/api/v1/prices/moving-average/AAPL")
    assert response.status_code == 200
    ma_data = response.json()
    assert ma_data["symbol"] == "AAPL"
    assert isinstance(ma_data["moving_average"], float)
    assert ma_data["period"] == 5


def test_e2e_polling_job():
    # 1. Start a polling job
    response = requests.post(f"{BASE_URL}/api/v1/prices/poll", json={
        "symbols": ["AAPL"],
        "interval": 10,  # 10 seconds for quick testing
        "provider": "alpha_vantage"
    })
    assert response.status_code == 202
    job_data = response.json()
    job_id = job_data["job_id"]
    assert job_data["status"] == "accepted"
    
    # 2. Check the job status
    time.sleep(2)  # Give the job time to start
    response = requests.get(f"{BASE_URL}/api/v1/prices/poll/{job_id}")
    assert response.status_code == 200
    job_status = response.json()
    assert job_status["job_id"] == job_id
    assert job_status["status"] in ["active", "pending"]
    
    # 3. Wait for some polling cycles
    time.sleep(15)
    
    # 4. Check that we have more price points
    response = requests.get(f"{BASE_URL}/api/v1/prices/history/AAPL?hours=1")
    assert response.status_code == 200
    history = response.json()
    assert len(history) > 0
    
    # 5. Stop the job
    response = requests.delete(f"{BASE_URL}/api/v1/prices/poll/{job_id}")
    assert response.status_code == 200
    stop_data = response.json()
    assert stop_data["job_id"] == job_id
    assert stop_data["status"] == "stopped" 