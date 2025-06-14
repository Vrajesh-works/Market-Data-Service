import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from confluent_kafka import Producer
from app.core.config import settings

logger = logging.getLogger(__name__)

# Kafka producer for publishing market data events

class KafkaProducer:

    
    def __init__(self):
        self.config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'market-data-producer',
            'acks': 'all',
            'retries': 3,   
            'retry.backoff.ms': 1000,
        }
        self.producer = None
        self._initialize_producer()
    
    def _initialize_producer(self):
        try:
            self.producer = Producer(self.config)
            logger.info("Kafka producer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
    
    def _delivery_callback(self, error, message):
        if error:
            logger.error(f"Message delivery failed: {error}")
        else:
            logger.debug(f"Message delivered to {message.topic()} [{message.partition()}] at offset {message.offset()}")
    
    def publish_price_event(self, symbol: str, price: float, timestamp: datetime, 
                           provider: str, raw_response_id: str) -> bool:
    
        #Publish a price event to the price-events topic
        
        if not self.producer:
            logger.warning("Kafka producer not available, skipping message")
            return False
        
        message = {
            "symbol": symbol.upper(),
            "price": price,
            "timestamp": timestamp.isoformat(),
            "source": provider,
            "raw_response_id": str(raw_response_id)
        }
        
        try:
            message_json = json.dumps(message)
            
            self.producer.produce(
                topic=settings.KAFKA_TOPIC_PRICE_EVENTS,
                key=symbol, 
                value=message_json,
                callback=self._delivery_callback
            )
            
            self.producer.poll(0)
            
            logger.info(f"Published price event for {symbol}: ${price}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish price event for {symbol}: {e}")
            return False
    
    def flush(self, timeout: float = 10.0):
        if self.producer:
            self.producer.flush(timeout)
    
    def close(self):
        if self.producer:
            self.producer.flush(10.0) 
            logger.info("Kafka producer closed")


# Global producer instance
kafka_producer = KafkaProducer()