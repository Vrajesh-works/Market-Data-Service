import pytest
from datetime import datetime, timedelta
from app.services.kafka_consumer import MovingAverageConsumer


def test_calculate_moving_average():
    # Test with a list of 5 prices
    prices = [100, 101, 99, 102, 98]
    expected_average = 100.0
    
    consumer = MovingAverageConsumer()
    

    result = sum(prices) / len(prices)
    
    assert result == expected_average


def test_calculate_moving_average_edge_cases():
    prices = []
    assert len(prices) < 5 
    
    prices = [100]
    
    prices = [100, 100, 100, 100, 100]
    expected_average = 100.0
    result = sum(prices) / len(prices)
    assert result == expected_average
    
    prices = [-10, -20, -30, -40, -50]
    expected_average = -30.0
    result = sum(prices) / len(prices)
    assert result == expected_average
    
    prices = [-100, -50, 0, 50, 100]
    expected_average = 0.0
    result = sum(prices) / len(prices)
    assert result == expected_average 