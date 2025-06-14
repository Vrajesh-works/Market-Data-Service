import requests
import time

BASE_URL = "http://localhost:8000"

def test_task2():
    print("🧪 Testing Task 2: Database & Market Data Integration")
    
    # 1. Health check
    response = requests.get(f"{BASE_URL}/health")
    print(f"✅ Health check: {response.json()['status']}")
    
    # 2. Get latest price (stores in DB)
    response = requests.get(f"{BASE_URL}/api/v1/prices/latest?symbol=AAPL")
    print(f"✅ Latest price: ${response.json()['price']}")
    
    # 3. Get price history
    response = requests.get(f"{BASE_URL}/api/v1/prices/history/AAPL")
    print(f"✅ Price history: {len(response.json())} records")
    
    # 4. Start polling job
    response = requests.post(f"{BASE_URL}/api/v1/prices/poll", json={
        "symbols": ["AAPL"],
        "interval": 60
    })
    job_id = response.json()['job_id']
    print(f"✅ Polling job started: {job_id}")
    
    print("🎉 Task 2 verification complete!")

if __name__ == "__main__":
    test_task2()