import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from confluent_kafka import Consumer, KafkaError, Producer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import db_manager
from app.services.data_access import DataAccessLayer

logger = logging.getLogger(__name__)


class MovingAverageConsumer:
    
    def __init__(self):
        self.consumer_config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'moving-average-calculator',
            'client.id': 'ma-consumer',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,  
        }
        
        self.producer_config = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'client.id': 'ma-producer',
            'acks': 'all',
            'retries': 3,
        }
        
        self.consumer = None
        self.producer = None
        self.running = False
        self._initialize()
    
    def _initialize(self):
        try:
            self.consumer = Consumer(self.consumer_config)
            self.producer = Producer(self.producer_config)
            
            self.consumer.subscribe([settings.KAFKA_TOPIC_PRICE_EVENTS])
            
            logger.info("Moving Average Consumer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Moving Average Consumer: {e}")
    
    def _calculate_moving_average(self, symbol: str, db: Session) -> float:
        try:
            dal = DataAccessLayer(db)
            
            recent_prices = dal.get_last_n_prices(symbol, n=5)
            
            if len(recent_prices) < 5:
                logger.warning(f"Not enough data points for {symbol} moving average: {len(recent_prices)}")
                return None
            
            prices = [p.price for p in recent_prices]
            moving_avg = sum(prices) / len(prices)
            
            logger.info(f"Calculated 5-point MA for {symbol}: {moving_avg:.2f}")
            return moving_avg
            
        except Exception as e:
            logger.error(f"Error calculating moving average for {symbol}: {e}")
            return None
    
    def _publish_moving_average(self, symbol: str, moving_average: float, timestamp: datetime):
        try:
            message = {
                "symbol": symbol,
                "moving_average": moving_average,
                "period": 5,
                "timestamp": timestamp.isoformat(),
                "calculated_at": datetime.utcnow().isoformat()
            }
            
            message_json = json.dumps(message)
            
            self.producer.produce(
                topic=settings.KAFKA_TOPIC_SYMBOL_AVERAGES,
                key=symbol,
                value=message_json
            )
            
            self.producer.poll(0)
            logger.info(f"Published moving average for {symbol}: {moving_average:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to publish moving average for {symbol}: {e}")
    
    def _process_price_event(self, message_data: Dict[str, Any]):
        try:
            symbol = message_data.get('symbol')
            price = message_data.get('price')
            timestamp_str = message_data.get('timestamp')
            
            if not all([symbol, price, timestamp_str]):
                logger.error(f"Invalid message data: {message_data}")
                return
            
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            logger.info(f"Processing price event: {symbol} @ ${price}")
            
            with db_manager.get_session() as db:
                dal = DataAccessLayer(db)
                
                moving_avg = self._calculate_moving_average(symbol, db)
                
                if moving_avg is not None:
                    dal.save_moving_average(symbol, moving_avg, period=5)
                    
                    self._publish_moving_average(symbol, moving_avg, timestamp)
                
        except Exception as e:
            logger.error(f"Error processing price event: {e}")
    
    def start_consuming(self):
        if not self.consumer:
            logger.error("Consumer not initialized")
            return
        
        self.running = True
        logger.info("Starting Moving Average Consumer...")
        
        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break
                
                try:
                    message_data = json.loads(msg.value().decode('utf-8'))
                    
                    self._process_price_event(message_data)
                    
                    self.consumer.commit(msg)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.stop_consuming()
    
    def stop_consuming(self):
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.flush(10.0)
        logger.info("Moving Average Consumer stopped")


# Global consumer instance
moving_average_consumer = MovingAverageConsumer()